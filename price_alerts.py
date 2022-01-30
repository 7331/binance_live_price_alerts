#!/usr/bin/env python3.9
import asyncio
import traceback

from typing import Optional
from aiohttp import ClientSession, ClientTimeout


def _get_formatted_price(price: float, exclude_change_symbol: bool = True) -> str:
    change_symbol = '' if exclude_change_symbol or price == 0 else '+' if price > 0 else '-'
    return f'{change_symbol}${abs(price):,.4f}'


async def check_forever(market_pairs, default_webhooks):
    async with ClientSession(headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36'}, raise_for_status=True, timeout=ClientTimeout(total=10)) as client:
        while True:
            try:
                async with client.ws_connect('wss://stream.binance.com/stream') as ws:
                    await ws.send_json({'method': 'SUBSCRIBE', 'params': [market_pair.lower() + '@kline_1m' for market_pair in market_pairs], 'id': 1})

                    while True:
                        data: Optional[dict] = (await ws.receive_json()).get('data')

                        if not data:
                            continue

                        slug: str = data['s']
                        market_pair: dict = market_pairs[slug]
                        cached_price: Optional[float] = market_pair.get('cached_price')
                        current_price = float(data['k']['c'])

                        if not cached_price:
                            market_pair['cached_price'] = current_price
                            continue

                        cached_price_formatted = _get_formatted_price(cached_price)
                        current_price_formatted = _get_formatted_price(current_price)
                        print(f'[{slug}] {cached_price_formatted} -> {current_price_formatted}')
                        difference = current_price - cached_price

                        if abs(difference) >= market_pair['interval']:
                            market_pair['cached_price'] = current_price  # TODO: In order to not use a lock and minimize missed/repeated notifications, the POST requests should be retried up to N times.
                            description = f'**Price**: {current_price_formatted}'
                            description += f'\n**Change**: {_get_formatted_price(difference, exclude_change_symbol=False)}'

                            embeds = [
                                {
                                    'title': slug,
                                    'description': description,
                                    'url': f'https://www.binance.com/en/trade/{slug}?type=spot',
                                    'color': 14495300 if difference < 0 else 7975256
                                }
                            ]

                            webhook: dict
                            for webhook in market_pair.get('webhooks', default_webhooks):
                                await client.post(webhook['url'], json={'username': 'Price Change!', 'avatar_url': 'https://public.bnbstatic.com/image/cms/blog/20200707/631c823b-886e-4e46-b12f-29e5fdc0882e.png', 'content': webhook['content'], 'embeds': embeds})

            except:
                print('Something went wrong, reconnecting: ' + traceback.format_exc(3))
                await asyncio.sleep(5)


def main():
    default_webhooks = [
        {
            'url': '', # Discord webhook
            'content': '' # if you need to tag a role, or say something
        }
    ]

    market_pairs = {
        'BTCUSDT': {
             'interval': 750
         },
         'ETHUSDT': {
             'interval': 100
         },
         'BNBUSDT': {
             'interval': 50
         },
         'ADAUSDT': {
             'interval': 0.05
         },
         'DOGEUSDT': {
             'interval': 0.025
         },
         'XRPUSDT': {
             'interval': 0.15
         },
         'DOTUSDT': {
             'interval': 2.5
         },
         'LTCUSDT': {
             'interval': 10
         },
         'LINKUSDT': {
             'interval': 5
         }
    }

    asyncio.run(check_forever(market_pairs, default_webhooks))


if __name__ == '__main__':
    main()
