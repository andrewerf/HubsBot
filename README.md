# HubsBot

---

This is a course project for BICA taught in MEPhI by Alexei Samsonovich.
The main goal is to create an easy-to-use programmatic API for [Mozilla Hubs](https://hubs.mozilla.com/).

## Comparison to analogues

There are quite a few similar pieces of software freely available, however none of them seem to provide an ability to use voice-chat features of the Hubs.
The voice, however, is very important for any research involving the Human-AI interaction.

Therefore, the main feature of this project is that it **allows to receive and send voice messages** and **control position and other properties of the avatar** in Hubs by means of simple and minimalistic API, which the Hubs itself seems to lack.

## Dependencies

- pymediasoup -- Hubs voice capabilities are based on the MediaSoup protocol, which is inherited from the WebRTC.
This library provides a python wrapper for this protocol. Note that it strictly requires Python <= 3.10 to build without errors;
- hubsclient -- simple GraphQL wrapper for rooms and other avatars interactions;
- aiortc -- required for audio acquisition.

