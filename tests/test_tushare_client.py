from nano_tradingagents.data.tushare_client import create_tushare_pro_client, DEFAULT_TUSHARE_HTTP_URL


class FakePro:
    def __init__(self):
        self._DataApi__http_url = None


class FakeTS:
    def __init__(self):
        self.last_token = None

    def pro_api(self, token):
        self.last_token = token
        return FakePro()


def test_create_tushare_pro_client_sets_http_url():
    fake_ts = FakeTS()
    pro = create_tushare_pro_client(token="abc", ts_module=fake_ts)
    assert fake_ts.last_token == "abc"
    assert pro._DataApi__http_url == DEFAULT_TUSHARE_HTTP_URL


def test_create_tushare_pro_client_custom_http_url():
    fake_ts = FakeTS()
    pro = create_tushare_pro_client(token="abc", ts_module=fake_ts, http_url="http://example.com:8010/")
    assert pro._DataApi__http_url == "http://example.com:8010/"
