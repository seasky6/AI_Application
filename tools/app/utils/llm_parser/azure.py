import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI,AzureOpenAIEmbeddings
import base64
load_dotenv()



class Azure:

    def __init__(self):
        pass


    def generate_embeddings(self, texts: list[str]):
        embeddings = AzureOpenAIEmbeddings(
            model=os.environ["OPENAI_MODEL_NAME_EMBEDDING"],
            # Use custom embedding model name from environment variable
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key= base64.b64decode(os.environ["AZURE_OPENAI_API_KEY"]).decode() ,
            openai_api_version=os.environ["OPENAI_API_VERSION_EMBEDDING"],  # Correct API version for embedding
            openai_api_type="azure",  # Specify the API type
        )
        vectors = []
        try:
            vectors = embeddings.embed_documents(texts)
        except Exception as e:
            print(f"Error occurred: {e}")
        return vectors


    def chat(self, messages: list[dict[str, str]]):
        llm = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=base64.b64decode(os.environ["AZURE_OPENAI_API_KEY"]).decode(),
        azure_deployment=os.environ["OPENAI_MODEL_NAME_LLM"],  # Correct deployment model
            api_version=os.environ["OPENAI_API_VERSION_LLM"],
            temperature=os.environ["TEMPERATURE"],
            top_p=os.environ["TOP_P"],
            max_tokens=os.environ["MAX_TOKENS"]
        )
        response = ""
        try:
            llm_response = llm.invoke(messages)
            response = llm_response.content
        except Exception as e:
            print(f"Error occurred: {e}")
        return response
    def get_llm(self):
        llm = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key= base64.b64decode(os.environ["AZURE_OPENAI_API_KEY"]).decode()  ,
            azure_deployment=os.environ["OPENAI_MODEL_NAME_LLM"],  # Correct deployment model
            api_version=os.environ["OPENAI_API_VERSION_LLM"],
            temperature=os.environ["TEMPERATURE"],
            top_p=os.environ["TOP_P"],
            max_tokens=os.environ["MAX_TOKENS"]
        )
        return llm

if __name__ == '__main__':
    azure = Azure()
    messages =  [
        {
       "role": "system",
       "content": "you're a helpful assistant that talks like a pirate"
      },
      {
       "role": "user",
       "content": "can you tell me how to care for a parrot?"
      }
    ]

    print(azure.chat(messages))
