from tavily import TavilyClient
import os

class WebSearchClient:

    def __init__(self, api_key):
        self.client = TavilyClient(api_key=api_key)

    def search(self, query):

        response = self.client.search(
            query=query,
            search_depth="advanced",
            max_results=5
        )

        results = []
        for r in response["results"]:
            results.append(r["content"])

        return results