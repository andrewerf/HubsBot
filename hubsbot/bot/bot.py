import asyncio
import json
from random import random
from typing import Dict, List, Tuple
from urllib.parse import urlparse # for ``from_sharing_link``
from hubsclient import HubsClient
from aiortc.mediastreams import VideoStreamTrack, MediaStreamTrack
import websockets
from pymediasoup import Device, AiortcHandler
from pymediasoup.consumer import Consumer
from pymediasoup.data_consumer import DataConsumer
from pymediasoup.producer import Producer
from pymediasoup.sctp_parameters import SctpStreamParameters
from pymediasoup.transport import Transport

from hubsbot.consumer import ConsumerFactory, VoiceConsumer, TextConsumer, Message
from hubsbot.peer import Peer


def generateRandomNumber() -> int:
    return round(random()*10000000)


class Bot:
    def __init__(self,
                 host: str,
                 room_id: str,
                 avatar_id: str,
                 display_name: str,
                 consumer_factory: ConsumerFactory,
                 voice_track: MediaStreamTrack):
        """
        This is the main class of the HubsBot.
        It combines avatar management, voice chat and text chat in the single interface.

        :param host:
        :param rood_id:
        :param avatar_id:
        :param display_name:
        :param consumer_factory:
            Factory of media consumers.
            When a new peer is connected to the room, this factory is used to create consumers specifically for him.
        :param voice_track: Voice track for this (local) peer
        """
        self.hubs_client = HubsClient(host, room_id, avatar_id, display_name)
        self.consumer_factory = consumer_factory

        self.room_id = room_id

        self.video_track = VideoStreamTrack()
        self.audio_track = voice_track
        self.media_device = Device(handlerFactory=AiortcHandler.createFactory(tracks=[self.video_track, self.audio_track]))

        self.pending_mediasoup_requests: Dict[int, asyncio.Future] = {}

        # Filled in ``join``
        self.voice_host = None
        self.voice_token = None
        self.voice_socket = None
        self.voice_peer_id = None
        self.recv_transport: Transport | None = None
        self.send_transport: Transport | None = None

        # Filled in ``_start_mediasoup_producing``
        self.audio_producer: Producer | None = None
        self.video_producer: Producer | None = None

        # Filled in ``_on_mediasoup_new_consumer``
        self.consumers: List[Tuple[VoiceConsumer | None, Consumer | DataConsumer]] = []
        self.text_consumers: Dict[str, TextConsumer] = {}

        # Filled in ``_hubs_receive``
        self.peers: Dict[str, Peer] = {}

    @classmethod
    def from_sharing_url(cls,
                         url: str,
                         avatar_id: str,
                         display_name: str,
                         consumer_factory: ConsumerFactory,
                         voice_track: MediaStreamTrack):
        """
        Given a sharing url (Share button in the room) creates a new bot in this room

        :param link: The url (e.g. https://9de36d10e9.us2.myhubs.net/link/NUCedZ2)
        :param avatar_id: check ``__init__``
        :param display_name: check ``__init__``
        :param consumer_factory: check ``__init__``
        :return: a newly created Bot
        """
        p = urlparse(url)
        return Bot(p.netloc, p.path.split('/')[2], avatar_id, display_name, consumer_factory, voice_track)

    async def close(self):
        await self.hubs_client.close()
        for voice_consumer, consumer in self.consumers:
            if voice_consumer is not None:
                await voice_consumer.stop()
            await consumer.close()

        await self.audio_producer.close()
        await self.video_producer.close()

        for task in self.pending_mediasoup_requests.values():
            task.cancel()

        await self.recv_transport.close()
        await self.send_transport.close()

    async def join(self):
        """
        Joins the room specified on construction
        """
        # join Hubs room and get token for the corresponding voice room
        await self.hubs_client.join()
        t1 = asyncio.create_task(self._hubs_receive())

        # perms_token is a token for the mediasoup client
        self.voice_token = self.hubs_client.sessinfo['perms_token']

        # host is the host of the mediasoup server
        self.voice_host = self.hubs_client.sessinfo['hubs'][0]['host'] + ':4443'

        # voice peer id corresponding to the Hubs peer id
        self.voice_peer_id = self.hubs_client.sid

        self.voice_socket = await websockets.connect(f'wss://{self.voice_host}/?roomId={self.room_id}&peerId={self.voice_peer_id}', subprotocols=['protoo'])
        t2 = asyncio.create_task(self._mediasoup_receive())
        await self._load_mediasoup()
        self.recv_transport = await self._create_mediasoup_recv_transport()
        self.send_transport = await self._create_mediasoup_send_transport()
        await self._start_mediasoup_producing()

        await asyncio.gather(t1, t2)

    async def _hubs_receive(self):
        """
        Reads everything from hubsclient and updates ``peers`` dict.
        """
        def peer_from_metas(id, metas) -> Peer:
            print(f'Adding peer {id}')
            return Peer(id=id, display_name=metas[0]['profile']['displayName'], position=[0.0, 0.0, 0.0])

        def presence_diff(data: dict):
            for k in data['leaves'].keys():
                self.peers.pop(k)

            for k, v in data['joins'].items():
                self.peers[k] = peer_from_metas(k, v['metas'])

        def presense_state(data: dict):
            for k, v in data.items():
                self.peers[k] = peer_from_metas(k, v['metas'])

        def naf(data: dict):
            k = data['from_session_id']
            self.peers[k].update_from_naf(data['data'])

        async def message(data: dict):
            body = data['body']
            await self.text_consumers[data['session_id']].on_message(Message(body=body))

        while True:
            await asyncio.sleep(0.1)
            msg = await self.hubs_client.get_message()
            msg = json.loads(msg.to_json())
            if msg[3] == 'presence_diff':
                presence_diff(msg[4])
            elif msg[3] == 'presence_state':
                presense_state(msg[4])
            elif msg[3] == 'naf':
                naf(msg[4])
            elif msg[3] == 'message':
                await message(msg[4])

    # ---
    # The following functions are mediasoup protocol's internals

    async def _send_mediasoup_request(self, req: dict):
        # create an empty future, that would be set when corresponding message is received
        # in _on_mediasoup_message_received
        self.pending_mediasoup_requests[req['id']] = asyncio.get_running_loop().create_future()
        await self.voice_socket.send(json.dumps(req))

    async def _wait_for_mediasoup_response(self, id: int, timeout=20):
        return await asyncio.wait_for(self.pending_mediasoup_requests[id], timeout=timeout)

    async def _load_mediasoup(self):
        req_id = generateRandomNumber()
        req = {'request': True, 'id': req_id, 'method': 'getRouterRtpCapabilities', 'data': {}}
        await self._send_mediasoup_request(req)
        resp = await self._wait_for_mediasoup_response(req_id)

        # Load Router RtpCapabilities
        await self.media_device.load(resp['data'])

    async def _create_mediasoup_send_transport(self) -> Transport:
        """
        Creates a send Transport (see mediasoup docs for ref)
        """
        req_id = generateRandomNumber()
        req = {
            'request': True,
            'id': req_id,
            'method': 'createWebRtcTransport',
            'data': {
                'forceTcp': False,
                'producing': True,
                'consuming': False,
                'sctpCapabilities': self.media_device.sctpCapabilities.dict()
            }
        }
        await self._send_mediasoup_request(req)
        resp = await self._wait_for_mediasoup_response(req_id)

        # Create sendTransport
        send_transport = self.media_device.createSendTransport(
            id=resp['data']['id'],
            iceParameters=resp['data']['iceParameters'],
            iceCandidates=resp['data']['iceCandidates'],
            dtlsParameters=resp['data']['dtlsParameters'],
            sctpParameters=resp['data']['sctpParameters']
        )

        @send_transport.on('connect')
        async def on_connect(dtlsParameters):
            req_id = generateRandomNumber()
            req = {
                "request": True,
                "id": req_id,
                "method": "connectWebRtcTransport",
                "data": {
                   "transportId": send_transport.id,
                   "dtlsParameters": dtlsParameters.dict(exclude_none=True)
                }
            }
            await self._send_mediasoup_request(req)
            await self._wait_for_mediasoup_response(req_id)

        @send_transport.on('produce')
        async def on_produce(kind: str, rtpParameters, appData: dict):
            req_id = generateRandomNumber()
            req = {
                "id": req_id,
                'method': 'produce',
                'request': True,
                'data': {
                    'transportId': send_transport.id,
                    'kind': kind,
                    'rtpParameters': rtpParameters.dict(exclude_none=True),
                    'appData': appData
                }
            }
            await self._send_mediasoup_request(req)
            resp = await self._wait_for_mediasoup_response(req_id)
            return resp['data']['id']

        @send_transport.on('producedata')
        async def on_producedata(sctpStreamParameters: SctpStreamParameters, label: str, protocol: str, appData: dict):
            req_id = generateRandomNumber()
            req = {
                "id": req_id,
                'method': 'produceData',
                'request': True,
                'data': {
                   'transportId': send_transport.id,
                   'label': label,
                   'protocol': protocol,
                   'sctpStreamParameters': sctpStreamParameters.dict(exclude_none=True),
                   'appData': appData
                }
            }
            await self._send_mediasoup_request(req)
            resp = await self._wait_for_mediasoup_response(req_id)
            return resp['data']['id']

        return send_transport

    async def _create_mediasoup_recv_transport(self) -> Transport:
        """
        Creates a receiver Transport (see mediasoup docs for ref)
        """
        req_id = generateRandomNumber()
        req = {
            'request': True,
            'id': req_id,
            'method': 'createWebRtcTransport',
            'data': {
                'forceTcp': False,
                'producing': False,
                'consuming': True,
                'sctpCapabilities': self.media_device.sctpCapabilities.dict()
            }
        }
        await self._send_mediasoup_request(req)
        resp = await self._wait_for_mediasoup_response(req_id)
        recv_transport = self.media_device.createRecvTransport(
            id=resp['data']['id'],
            iceParameters=resp['data']['iceParameters'],
            iceCandidates=resp['data']['iceCandidates'],
            dtlsParameters=resp['data']['dtlsParameters'],
            sctpParameters=resp['data']['sctpParameters']
        )

        @recv_transport.on('connect')
        async def on_connect(dtlsParameters):
            req_id = generateRandomNumber()
            req = {
                "request": True,
                "id": req_id,
                "method": "connectWebRtcTransport",
                "data": {
                    "transportId": recv_transport.id,
                    "dtlsParameters": dtlsParameters.dict(exclude_none=True)
                }
            }
            await self._send_mediasoup_request(req)
            await self._wait_for_mediasoup_response(req_id)

        return recv_transport

    async def _start_mediasoup_producing(self):
        req_id = generateRandomNumber()
        req = {
            "request": True,
            "id": req_id,
            "method": "join",
            "data": {
                "displayName": "0359749b-d457-4a8a-8d47-8ce682f08da5",
                "device": {"flag": "python", "name": "python", "version": "0.1.0"},
                "rtpCapabilities": self.media_device.rtpCapabilities.dict(exclude_none=True),
                "sctpCapabilities": self.media_device.sctpCapabilities.dict(exclude_none=True),
                "token": f'{self.voice_token}'
            }
        }
        await self._send_mediasoup_request(req)
        await self._wait_for_mediasoup_response(req_id)

        # produce
        self.video_producer = await self.send_transport.produce(track=self.video_track, stopTracks=False, appData={})
        self.audio_producer = await self.send_transport.produce(track=self.audio_track, stopTracks=False, appData={})

    async def _mediasoup_receive(self):
        """
        Reads everything that is sent by mediasoup server.
        Calls _on_new_consumer if  'method': 'newPeer' is received, and manages pending_mediasoup_requests.
        """
        while True:
            msg = await self.voice_socket.recv()
            msg = json.loads(msg)
            if msg.get('response'):
                self.pending_mediasoup_requests[msg['id']].set_result(msg)
            elif msg.get('request'):
                if msg['method'] == 'newConsumer':
                    await self._on_mediasoup_new_consumer(
                        id=msg['data']['id'],
                        producer_id=msg['data']['producerId'],
                        peer_id=msg['data']['peerId'],
                        kind=msg['data']['kind'],
                        rtp_parameters=msg['data']['rtpParameters']
                    )
                    response = {'response': True, 'id': msg['id'], 'ok': True, 'data': {}}
                    await self.voice_socket.send(json.dumps(response))
                elif msg.get('method') == 'newDataConsumer':
                    await self._on_mediasoup_new_data_consumer(
                        id=msg['data']['id'],
                        data_producer_id=msg['data']['dataProducerId'],
                        label=msg['data']['label'],
                        protocol=msg['data']['protocol'],
                        sctp_stream_parameters=msg['data']['sctpStreamParameters'],
                        appData={}
                    )
                    response = {'response': True, 'id': msg['data']['id'], 'ok': True, 'data': {}}
                    await self.voice_socket.send(json.dumps(response))
            elif msg.get('notification'):
                print(msg)

    async def _on_mediasoup_new_consumer(self, id: str, producer_id: str, peer_id: str, kind: str, rtp_parameters: dict):
        """
        Called when a new remote voice-producer is joined the room.
        Sets up the consumer for this producer
        """
        mediasoup_consumer = await self.recv_transport.consume(id=id, producerId=producer_id, kind=kind, rtpParameters=rtp_parameters)
        consumer = self.consumer_factory.create_voice_consumer(self.peers[peer_id], mediasoup_consumer.track)
        self.consumers.append((consumer, mediasoup_consumer))
        self.text_consumers[peer_id] = self.consumer_factory.create_text_consumer(self.peers[peer_id])
        asyncio.create_task(consumer.start())

    async def _on_mediasoup_new_data_consumer(self, id: str, data_producer_id: str, sctp_stream_parameters: dict,
                                              label: str, protocol: str, appData: dict):
        """
        DataConsumers are not used by Hubs, but it seems to be necessary to initialize one to get the protocol working :/
        """
        dataConsumer = await self.recv_transport.consumeData(
            id=id, dataProducerId=data_producer_id,
            sctpStreamParameters=sctp_stream_parameters,
            label=label,
            protocol=protocol,
            appData=appData
        )
        self.consumers.append((None, dataConsumer))

        @dataConsumer.on('message')
        def on_message(message):
            print(f'DataChannel {label}-{protocol}: {message}')