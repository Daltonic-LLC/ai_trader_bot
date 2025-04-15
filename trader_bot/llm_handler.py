from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class LLMHandler:
    """Handles interactions with the language model for summarization and decision-making, executing trading actions directly."""
    
    def __init__(self, base_url, model, temperature, timeout):
        self.chat_model = ChatOllama(base_url=base_url, model=model, temperature=temperature, timeout=timeout)

    def buy(self, coin: str) -> str:
        """Simulates buying the coin and returns the decision."""
        print(f"AI Agent: Buying {coin.upper()}")
        return "BUY"

    def sell(self, coin: str) -> str:
        """Simulates selling the coin and returns the decision."""
        print(f"AI Agent: Selling {coin.upper()}")
        return "SELL"

    def hold(self, coin: str) -> str:
        """Simulates holding the coin and returns the decision."""
        print(f"AI Agent: Holding {coin.upper()}")
        return "HOLD"

    def summarize(self, text):
        """Summarizes the given text using the LLM (no longer used for decision-making)."""
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

    def decide(self, coin, current_price, predicted_close, news_sentiment, news_text):
        """Makes a trading decision (Buy, Sell, Hold) and executes the action directly."""
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
        if decision == "BUY":
            return self.buy(coin)
        elif decision == "SELL":
            return self.sell(coin)
        elif decision == "HOLD":
            return self.hold(coin)
        else:
            # Fallback to hold if the decision is invalid
            return self.hold(coin)