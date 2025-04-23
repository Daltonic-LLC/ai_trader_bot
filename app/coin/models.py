from pydantic import BaseModel, Field


class CrawlRequest(BaseModel):
    title: str = Field(..., description="Site Title", example="Ollama Models Released")
    url: str = Field(
        ..., description="URL to scrape", example="https://ollama.com/search"
    )
