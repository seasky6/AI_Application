import base64
import json
import os

from langchain_openai import AzureChatOpenAI

from app.services.log_parser.llm_parser.azure import Azure


class LLM():
    def __init__(self, user_query_msg, system_msg ):
        self.user_query_msg = user_query_msg
        self.system_msg = system_msg


    def get_prompt(self, context):
        prompt_contexts = f"Contexts:\n{context}\n\n"
        prompt_question = f"Question:\n{self.user_query_msg}"
        prompt = f"{prompt_contexts}{prompt_question}".strip()
        messages = [
            {"role": "system", "content": self.system_msg},
            {"role": "user", "content": prompt},
        ]
        return messages

    def query_no_agent(self):
        source_text = []
        messages = self.get_prompt("messsage")

        azure = Azure()
        response = azure.chat(messages=messages)
        print(response)
        result = {
            "response": response,
            "SourceText": source_text
        }
        return result
    def get_llm(self):
        llm = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key= base64.b64decode(os.environ["AZURE_OPENAI_API_KEY"]).decode(),
            azure_deployment=os.environ["OPENAI_MODEL_NAME_LLM"],  # Correct deployment model
            api_version=os.environ["OPENAI_API_VERSION_LLM"],
            temperature=os.environ["TEMPERATURE"],
            top_p=os.environ["TOP_P"],
            max_tokens=os.environ["MAX_TOKENS"]
        )
        return llm

    def generate_regex_from_llm(self,log_text: str) -> dict:
        functions = [
            {
                "name": "extract_regex",
                "description": "为日志生成正则表达式",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "正则表达式"}
                        # "fields": {"type": "array", "items": {"type": "string"}, "description": "提取字段名"}
                    },
                    "required": ["pattern"]
                }
            }
        ]
        llm_temp = Azure()
        q_message = "i need a regex to make this log:%s to key and value" % log_text
        # q_message = """PA measured values for driver name: DpaVddSv:1; value: 46441; branch Id: 1 对应的正则'driver name: (?P<driver_name>\\w+):(?P<driver_id>\\d+); value: (?P<value>\\d+); branch Id: (?P<branch_id>\\d+)' 用程序kv_matches = re.finditer 匹配时，没有命中 帮我重新生成正则表达式"""
        system_message = (f"请为以下日志生成提取所有key value键值对的正则表达式,：\n{log_text}"
                          f"        要求："
                          f"- 每条日志中包含多个键值对"
                          f"- 不要捕获时间戳"
                          f"- 使用命名捕获组：key 对应 (?P<key>...)，value 对应 (?P<value>...),所以正则中应该只有一对P<key>和P<value>"
                          f"- 不需要额外说明，只返回一个完整的正则表达式字符串"
                          f"- 正则表达式用于re.finditer ")
#         system_message = """请为以下日志生成一个正则表达式，用于提取其中的每一组 key-value 键值对。
#
# 要求如下：
# - 每条日志中包含多个键值对，格式可能为 key: value 或 key = value
# - 使用命名捕获组：key 对应 (?P<key>...)，value 对应 (?P<value>...)
# - 每次只匹配一组 key-value 对，该正则表达式用于 re.finditer 遍历整条日志
# - key 可以包含空格或下划线（如 PA current、driver_name）
# - value 可以是任意字符串，包含字母、数字、单位、空格等
# - 不需要捕获时间戳
# - 仅返回一个正则表达式字符串，不需要说明
# """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": q_message},
        ]
        response = llm_temp.get_llm().invoke(
            input=messages,
            functions=functions,
            function_call={"name": "extract_regex"}
        )
        regex_json = response.additional_kwargs["function_call"]["arguments"]
        parsed = json.loads(regex_json)
        return parsed



if __name__ == '__main__':
    user_query_msg = """what is the weather like today"""
    system_msg = "You are a helpful assistant. think step by step"
    llm = LLM(user_query_msg=user_query_msg, system_msg=system_msg)
    result = llm.query_no_agent()
    print(result['response'])
    log_text= '42: Temperature: T_Mpa_A 433;340;485;419,T_Mpa_B 435;338;493;420,T_Mpa_C 430;338;493;417,T_Mpa_D 418;330;463;402'
    regex_llm = llm.generate_regex_from_llm(log_text)
    print(regex_llm)
