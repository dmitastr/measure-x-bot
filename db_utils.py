from kikimr.public.sdk.python import client as ydb
import logging
import os

logger = logging.getLogger('ydb_connection')

class YDataBase():
    def __init__(self):
        self.endpoint = os.getenv("YDB_ENDPOINT")
        self.database = os.getenv("YDB_DATABASE")
        if self.endpoint is None or self.database is None:
            raise AssertionError("Нужно указать обе переменные окружения")

    def execute_query(self, query): 
        with ydb.Driver(endpoint=self.endpoint, database=self.database) as driver:
            try:
                driver.wait(timeout=5)
            except TimeoutError:
                print("Connect failed to YDB")
                print("Last reported errors by discovery:")
                print(driver.discovery_debug_details())
                exit(1)
            session = driver.table_client.session().create()
            result_sets = session.transaction(ydb.SerializableReadWrite()).execute(
                query,
                commit_tx=True
            )
            result_parsed = []
            try:
                if result_sets:
                    result_parsed = [self.parse_row(row) for row in result_sets[0].rows]
            except Exception:
                logger.exception("Error while executing query", exc_info=True)
            return result_parsed

    def fetch_last_config(self, user_id: int=None) -> list:
        return self.execute_query(
            'SELECT * FROM measures WHERE {0} OR creator_id={1};'
        ).format('false' if user_id else 'true', user_id or -1)

    def parse_row(self, row):
        res_parsed = {}
        for k, v in dict(row).items():
            try: 
                value = v.decode()
            except (UnicodeDecodeError, AttributeError):
                value = v
            res_parsed[k] = value
        return res_parsed
