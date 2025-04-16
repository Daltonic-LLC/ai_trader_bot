from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class LLMHandler:
    """Handles interactions with the language model for decision-making, including arbitrage via BinanceClient."""
    
    def __init__(self, base_url, model, temperature, timeout, binance_api_key, binance_api_secret):
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
    
    def hold(self, coin: str) -> str:
        """Simulates holding the coin (no action on exchange) and returns the decision."""
        print(f"AI Agent: Holding {coin.upper()}")
        return "HOLD"

    def decide(self, coin, current_price, predicted_close, news_sentiment, news_text, enable_arbitrage: bool = True):
        """Makes a trading decision (Buy, Sell, Hold) or attempts arbitrage, then executes the action."""

        sentiment_label = "positive" if news_sentiment > 0 else "negative" if news_sentiment < 0 else "neutral"
        prompt_template = ChatPromptTemplate.from_template(
            """Given the following information about {coin}:
            - Current Price: ${current_price}
            - Predicted Close: ${predicted_close}
            - News Sentiment: {news_sentiment} ({sentiment_label})
            - News Text: '{news_text}'

            Based on this information, provide a single-word trading recommendation: Buy, Sell, or Hold. Do not provide explanations."""
        )
        input_data = {
            "coin": coin.upper(),
            "current_price": f"{current_price:.2f}",
            "predicted_close": f"{predicted_close:.2f}",
            "news_sentiment": f"{news_sentiment:.2f}",
            "sentiment_label": sentiment_label,
            "news_text": news_text
        }
        llm_chain = prompt_template | self.chat_model | StrOutputParser()
        decision = llm_chain.invoke(input_data).strip().upper()

        # Validate the decision and execute the corresponding action
        quantity = 1.0
        if decision == "BUY":
            return "BUY"
        elif decision == "SELL":
            return "SELL"
        else:
            return "HOLD"