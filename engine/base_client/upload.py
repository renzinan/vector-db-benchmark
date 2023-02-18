import time
from datetime import datetime
from multiprocessing import get_context
from typing import Iterable, List, Optional, Tuple

import tqdm

from dataset_reader.base_reader import Record
from engine.base_client.utils import iter_batches


class BaseUploader:
    client = None

    def __init__(self, host, connection_params, upload_params):
        self.host = host
        self.connection_params = connection_params
        self.upload_params = upload_params

    @classmethod
    def get_mp_start_method(cls):
        return None

    @classmethod
    def init_client(cls, host, distance, connection_params: dict, upload_params: dict):
        raise NotImplementedError()

    def upload(
        self,
        distance,
        records: Iterable[Record],
    ) -> dict:
        latencies = []
        upload_results = []
        start = time.perf_counter()
        start_timestamp = datetime.now().astimezone().isoformat()
        parallel = self.upload_params.pop("parallel", 1)
        batch_size = self.upload_params.pop("batch_size", 64)

        self.init_client(
            self.host, distance, self.connection_params, self.upload_params
        )

        if parallel == 1:
            for batch in iter_batches(tqdm.tqdm(records), batch_size):
                upload_results.append(self._upload_batch(batch))
        else:
            ctx = get_context(self.get_mp_start_method())
            with ctx.Pool(
                processes=int(parallel),
                initializer=self.__class__.init_client,
                initargs=(
                    self.host,
                    distance,
                    self.connection_params,
                    self.upload_params,
                ),
            ) as pool:
                upload_results = list(
                    pool.imap(
                        self.__class__._upload_batch,
                        iter_batches(tqdm.tqdm(records), batch_size),
                    )
                )
        
        latencies = [item[0] for item in upload_results]
        data_size = [item[1] for item in upload_results]
        dataset_size = sum(data_size)

        upload_time = time.perf_counter() - start
        end_upload_timestamp = datetime.now().astimezone().isoformat()
        
        print(f"Dataset size: {dataset_size}")
        print("Upload time: {}".format(upload_time))

        post_upload_stats = self.post_upload(distance)

        end_load_timestamp = datetime.now().astimezone().isoformat()
        total_time = time.perf_counter() - start

        print(f"Total import time: {total_time}")

        return {
            "post_upload": post_upload_stats,
            "dataset_size": dataset_size,
            "upload_time": upload_time,
            "total_time": total_time,
            "start_timestamp": start_timestamp,
            "end_upload_timestamp": end_upload_timestamp,
            "end_load_timestamp": end_load_timestamp,
            "latencies": latencies,
        }

    @classmethod
    def _upload_batch(
        cls, batch: Tuple[List[int], List[list], List[Optional[dict]]]
    ) -> (float, int):
        ids, vectors, metadata = batch
        start = time.perf_counter()
        cls.upload_batch(ids, vectors, metadata)
        return (time.perf_counter() - start, len(vectors))

    @classmethod
    def post_upload(cls, distance):
        return {}

    @classmethod
    def upload_batch(
        cls, ids: List[int], vectors: List[list], metadata: List[Optional[dict]]
    ):
        raise NotImplementedError()
