import re
import json
from datetime import datetime

from app.dto.logItemDto import LogItemDto
from app.services.log_parser.llm_parser.llm import LLM
global_index = 0
CONFIG_PATH = "configs/regex_patterns.json"
elog_time_id_pattern =  r"\[(?P<timestamp>\d{6} \d{6})\]\s+(?P<elog_id>\d+):"
def load_patterns() -> dict:
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_patterns(patterns: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(patterns, f, indent=2)

def process_log(log_text: str, patterns: list[dict],line_index:int) -> LogItemDto:
    match = re.search(elog_time_id_pattern, log_text)
    if not match:
        return None
    log_item_dto_list = []
    raw_ts = match.group("timestamp")  # 例如 "250317 141938"
    elog_id = match.group("elog_id")
    # 转换为 datetime 对象（注意年份前缀为 20XX）
    dt = datetime.strptime(raw_ts, "%y%m%d %H%M%S")
    # 格式化为字符串格式 "2025-03-17 14:19:38"
    formatted_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
    clean_log_content = log_text[match.end():]
    for pattern_info in patterns:
        pattern = pattern_info["regex"]
        if validate_regex(pattern, clean_log_content):
            kv_matches = re.finditer(pattern, clean_log_content)
            for m in kv_matches:
                item = LogItemDto(
                    index=get_next_index(),
                    timestamp=formatted_ts,
                    elog_id=elog_id,
                    content=log_text,
                    key=m.groupdict().get("key"),
                    value = m.groupdict().get("value"),
                parent_index=line_index
                )
                log_item_dto_list.append(item)
            return log_item_dto_list

    # 未匹配，调用大模型生成新正则
    new_info = LLM("","").generate_regex_from_llm(clean_log_content)
    new_index = max([p["index"] for p in patterns], default=0) + 1
    print("start to call llm for :%s"%new_info)

    if validate_regex(new_info["pattern"], clean_log_content):
        new_pattern = {
            "index": new_index,
            "regex": new_info["pattern"]
        }
        patterns.append(new_pattern)
        save_patterns(patterns)
        kv_matches = re.finditer(new_info["pattern"], clean_log_content)
        for m in kv_matches:
            item = LogItemDto(
                index=get_next_index(),
                timestamp=formatted_ts,
                elog_id=elog_id,
                content=log_text,
                key=m.groupdict().get("key"),
                value=m.groupdict().get("value"),
                parent_index=line_index
            )
            log_item_dto_list.append(item)
        return log_item_dto_list
    else:
        print("llm problem when handle %s" %log_text)
        return  None



def validate_regex(pattern: str, log_text: str)->bool:

    # 编译验证
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return False

    # 命名组检查
    if "(?P<key>" not in pattern or "(?P<value>" not in pattern:
        return False

    # 匹配测试
    matches = list(regex.finditer(log_text))
    if not matches:
        return False

    # 分组内容检查
    for m in matches:
        gdict = m.groupdict()
        if not gdict.get("key") or not gdict.get("value"):
            return False

    return True, matches

def get_next_index()->int:
    global global_index
    global_index += 1
    return global_index

if __name__ == '__main__':
    log_text_elog = '[230521 160000]   42: Temperature: T_Mpa_A 433;340;485;419,T_Mpa_B 435;338;493;420,T_Mpa_C 430;338;493;417,T_Mpa_D 418;330;463;402'
    # log_text_elog = '[240906 155959]   43: PA current: I_Mpa0_C 2100;1368;3246;1829,I_Mpa1_C 2100;1368;3245;1829'
    # log_text_elog = '[250130 182514]  27: PA measured values for driver name: PaVddSv:1; value: 45921; branch Id: 1'
    # log_text_elog = '[210323 074937]    1: RU start/restarted; Restart cause:PWR_ON; LMC ID: CXP2021138%1_R29H39 (AUBOOT)'
    # log_text_elog = '[250130 182514]  193: SerDes Eye Height: JESD link type: RX_ADC; endpoint: drxJesdSerDesRx:0.3; lane: 0, number of ranges: 10: 0, 0, 0, 0, 0, 0, 8639, 0, 0, 0;'
    log_text_elog = '[241012 052631]  104: TRX JESD LINK FAILURE: [paPInterruptSv:0]:jesd204AllLayersRxLinkPalau:0.0 Deframer interrupt happened, bits map:0x400 now status: OK'
    log_text_elog = '[250225 082033]  104: TRX JESD LINK FAILURE: jesd204AllLayersRxLinkPalau:0.0: Deframer interrupt happened, status OK after timeout, sv resynced'
    patterns = load_patterns()
    log_item_dto = process_log(log_text_elog,patterns,1)
    print(json.dumps(log_item_dto, default=lambda o: o.__dict__, ensure_ascii=False))
