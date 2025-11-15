

class MockSearchClient:
    async def search(self, *args, **kwargs):
        return {"hits": {"hits": []}}

async def test_search_service():
    service = SearchService(MockSearchClient())
    results = await service.search_documents("test", {})
    assert results == {"hits": {"hits": []}}