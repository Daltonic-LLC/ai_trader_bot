from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class LLMHandler:
    def __init__(self, base_url, model, temperature, timeout):
        self.chat_model = ChatOllama(base_url=base_url, model=model, temperature=temperature, timeout=timeout)

    def decide(self, report):
        """Decides trading recommendation based on the provided report text."""
        # Define the prompt
        prompt_template = ChatPromptTemplate.from_template(
            """Given the following daily report:

            {report}

            Based on this information, provide a single-word trading recommendation: Buy, Sell, or Hold."""
            )

        # Pass the report to the LLM
        input_data = {"report": report}
        llm_chain = prompt_template | self.chat_model | StrOutputParser()
        decision = llm_chain.invoke(input_data).strip().upper()

        return decision