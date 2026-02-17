"""Сравнение MongoDB и PostgreSQL для UGC-нагрузки"""
import asyncio
import random
import time
from datetime import datetime

import argparse
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient


async def benchmark_postgres(dsn: str, records: int, users: int, films: int) -> dict:
    conn = await asyncpg.connect(dsn)
    await conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS benchmark_reviews (
         id BIGSERIAL PRIMARY KEY,
         user_id INT NOT NULL,
         film_id INT NOT NULL,
         rating REAL NOT NULL,
         text TEXT NOT NULL,
         created_at TIMESTAMP NOT NULL
        );
        TRUNCATE benchmark_reviews;
        ''')

    start = time.perf_counter()
    batch_size = 5000

    for offset in range(0, records, batch_size):
        batch = [
            (
                random.randint(1, users),
                random.randint(1, films),
                random.randint(1, 10),
                'review text',
                datetime.now(),
            )
            for _ in range(min(batch_size, records - offset))
        ]
        await conn.executemany(
            'INSERT INTO benchmark_reviews (user_id, film_id, rating, text, created_at) VALUES ($1, $2, $3, $4, $5)',
            batch
        )

    write_sec = time.perf_counter() - start

    start = time.perf_counter()

    for _ in range(1000):
        await conn.fetch('SELECT * FROM benchmark_reviews WHERE film_id = $1 ORDER BY created_at DESC LIMIT 20',
                         random.randint(1, films))
    read_sec = time.perf_counter() - start
    await conn.close()
    return {'write_sec': write_sec, 'read_sec': read_sec}


async def benchmark_mongo(uri: str, records: int, users: int, films: int) -> dict:
    client = AsyncIOMotorClient(uri)
    db = client.benchmark
    await db.reviews.delete_many({})
    await db.reviews.create_index([('film_id', 1), ('created_at', -1)])

    start = time.perf_counter()
    batch_size = 5000

    for offset in range(0, records, batch_size):
        batch = [
            {
                'user_id': random.randint(1, users),
                'film_id': random.randint(1, films),
                'rating': random.randint(1, 10),
                'text': 'review text',
                'created_at': datetime.now(),
            }
            for _ in range(min(batch_size, records - offset))
        ]
        await db.reviews.insert_many(batch, ordered=False)
    write_sec = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(1000):
        cursor = db.reviews.find({'film_id': random.randint(1, films)}).sort('created_at', -1).limit(20)
        await cursor.to_list(length=20)
    read_sec = time.perf_counter() - start
    client.close()
    return {'write_sec': write_sec, 'read_sec': read_sec}


async def main() -> None:
    print("START")
    parser = argparse.ArgumentParser(description='Benchmark storage')
    parser.add_argument('--records', type=int, default=100_000_000)
    parser.add_argument('--users', type=int, default=10_000_000)
    parser.add_argument('--films', type=int, default=2_000_000)
    parser.add_argument('--postgres-dsn', default='postgresql://user:password@localhost:5433/db')
    parser.add_argument('--mongo-uri', default='mongodb://localhost:27017')
    args = parser.parse_args()
    print(args)

    pg = await benchmark_postgres(args.postgres_dsn, args.records, args.users, args.films)
    mongo = await benchmark_mongo(args.mongo_uri, args.records, args.users, args.films)

    print('PostgreSQL: ', pg)
    print('MongoDB:', mongo)


if __name__ == '__main__':
    asyncio.run(main())
