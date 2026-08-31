from Astandy.generated.schemes_pb2 import (
    SubscribeRequest,
    GetTradeOpenSaleRequestsRequest,
    SearchPlayersRequest,
)
from Astandy.types.service import Service
from Astandy.listener import Listener
from Astandy.generated.listeners import GeneratedEvent
import Astandy

class BoltRemoteService(Service):
    async def subscribe(self: 'Astandy.StandClient', topic: str):
        '''
        :param topic: topic name
        '''
        request = SubscribeRequest()
        request.topic = topic

        response = self.raw.BoltRemoteService.subscribe2Response(
            await self.send_request(
                *self.raw.BoltRemoteService.subscribe2Request(
                    request
                )
            )
        )

        return True

    async def get_trade_open_sale_requests(
        self: 'Astandy.StandClient',
        item_definition_id: int,
        page: int = 0,
        size: int = 100,
    ):
        """Load open sale requests, including the creator when the server exposes it."""
        request = GetTradeOpenSaleRequestsRequest(
            id=item_definition_id,
            page=page,
            size=size,
        )
        response = self.raw.MarketplaceRemoteService.getTradeOpenSaleRequests2Response(
            await self.send_request(
                *self.raw.MarketplaceRemoteService.getTradeOpenSaleRequests2Request(request)
            )
        )
        return response.openRequests

    async def search_players(
        self: 'Astandy.StandClient',
        name: str,
        page: int = 1,
        size: int = 20,
    ):
        """Search players by visible name and return PlayerFriend results."""
        request = SearchPlayersRequest(value=name, page=page, size=size)
        response = self.raw.FriendsRemoteService.searchPlayers2Response(
            await self.send_request(
                *self.raw.FriendsRemoteService.searchPlayers2Request(request)
            )
        )
        return response.playerFriends

    async def subscribe_trade(
        self: 'Astandy.StandClient',
        item_definition_id: int,
        on_new_lot=None,
    ):
        """Subscribe to new marketplace lots for an item.

        If ``on_new_lot`` is supplied, it is called as::

            await on_new_lot(client, request, player_id)

        where ``request`` is the protobuf ``OpenRequest``.  The player ID is
        taken from ``request.creator.gpid``; it is not the lot/request ID.
        ``request.creator.avatarId`` remains available as the avatar ID.
        """
        if on_new_lot is not None:
            class _NewLotListener(Listener):
                def __init__(self, callback, item_id):
                    super().__init__(callback)
                    self.item_id = item_id

                async def call(self, client, update):
                    event_request = update.data.request
                    if event_request.itemDefinitionId != self.item_id:
                        return

                    # The push event may anonymize creator.  Re-read the
                    # public sale list and replace it with the fuller record
                    # matching the event's lot ID, if one is available.
                    request = event_request
                    try:
                        requests = await client.get_trade_open_sale_requests(
                            self.item_id,
                            page=0,
                            size=100,
                        )
                        request = next(
                            (item for item in requests if item.id == event_request.id),
                            event_request,
                        )
                    except Exception:
                        # Keep delivery of the event even if the follow-up
                        # request is unavailable or temporarily fails.
                        pass

                    creator = request.creator
                    player_id = creator.gpid
                    await self._callback(client, request, player_id)

            # Depending on the marketplace operation, the server sends a new
            # lot through one of these two marketplace event pipelines.
            for event in (
                GeneratedEvent.MARKETPLACE_REMOTE_EVENT_LISTENER_ON_PLAYER_REQUEST_OPENED,
                GeneratedEvent.MARKETPLACE_REMOTE_EVENT_LISTENER_ON_TRADE_REQUEST_OPENED,
            ):
                listener = _NewLotListener(on_new_lot, item_definition_id)
                listener.event = event
                self._dp.add_listener(listener)

        return await self.subscribe(f"marketplace_trade_{item_definition_id}")
