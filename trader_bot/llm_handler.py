from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class LLMHandler:
    """Handles interactions with the language model for summarization and decision-making."""
    def __init__(self, base_url, model, temperature, timeout):
        self.chat_model = ChatOllama(base_url=base_url, model=model, temperature=temperature, timeout=timeout)

    def summarize(self, text):
        """Summarizes the given text using the LLM."""
        prompt_template = ChatPromptTemplate.from_template(
            """Summarize the following text in a single sentence of no more than 50 words.

            Text:
            {text}

            Summary:"""
        )
        llm_chain = (
            {"text": RunnablePassthrough()}
            | prompt_template
            | self.chat_model
            | StrOutputParser()
        )
        return llm_chain.invoke(text)

    def decide(self, coin, current_price, predicted_close, news_sentiment, news_summary):
        """Makes a trading decision (Buy, Sell, Hold) based on provided data."""
        decision_prompt_template = ChatPromptTemplate.from_template(
            """Given the following information about {coin}:
            - Current Price: ${current_price}
            - Predicted Close: ${predicted_close}
            - News Sentiment: {news_sentiment} ({sentiment_label})
            - News Summary: '{news_summary}'

            Based on this information, provide a single-word trading recommendation: Buy, Sell, or Hold."""
        )
        sentiment_label = "positive" if news_sentiment > 0 else "negative" if news_sentiment < 0 else "neutral"
        input_data = {
            "coin": coin.upper(),
            "current_price": f"{current_price:.2f}",
            "predicted_close": f"{predicted_close:.2f}",
            "news_sentiment": f"{news_sentiment:.2f}",
            "sentiment_label": sentiment_label,
            "news_summary": news_summary
        }
        llm_chain = decision_prompt_template | self.chat_model | StrOutputParser()
        response = llm_chain.invoke(input_data)
        decision = response.strip().upper()
        return decision if decision in ["BUY", "SELL", "HOLD"] else "HOLD"