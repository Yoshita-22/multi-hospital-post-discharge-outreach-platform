import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from app.services.voice.tts_provider import DeepgramTTSProvider

async def main():
    tts = DeepgramTTSProvider(os.getenv('DEEPGRAM_API_KEY'))
    res = await tts.synthesize('hello')
    print('LEN:', len(res))
    if len(res) > 0:
        print('START:', res[:20])
    
if __name__ == "__main__":
    asyncio.run(main())
