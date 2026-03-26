import os
import logging
from datetime import datetime


# 全局变量控制是否保存详细日志
_save_detailed_logs = False
_repair_info_logger = None
_log_file_path = None

# 设置固定的日志目录路径
FIXED_LOG_DIR = r"C:\Users\ehuabox\OneDrive - Ericsson\Desktop\Works\AI\AI for Log Analysis\deeplog\tools\files_parsed\logs"


def set_save_detailed_logs(enable):
    """设置是否保存详细日志"""
    global _save_detailed_logs
    _save_detailed_logs = enable


def get_log_file_path():
    """获取日志文件路径"""
    global _log_file_path
    return _log_file_path


def _get_repair_info_logger():
    """获取repair_info专用的日志记录器"""
    global _repair_info_logger, _log_file_path

    if _repair_info_logger is None:
        _repair_info_logger = logging.getLogger('repair_info')
        _repair_info_logger.setLevel(logging.DEBUG)

        # 避免重复添加处理器
        if not _repair_info_logger.handlers:
            # 创建控制台处理器（始终启用）
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 设置日志格式
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)

            # 添加控制台处理器
            _repair_info_logger.addHandler(console_handler)

        # 如果启用了详细日志保存，添加文件处理器
        if _save_detailed_logs and not _has_file_handler(_repair_info_logger):
            try:
                # 使用固定路径创建日志目录
                log_dir = FIXED_LOG_DIR
                os.makedirs(log_dir, exist_ok=True)
                _log_file_path = os.path.join(log_dir,
                                              f"repair_info_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

                file_handler = logging.FileHandler(_log_file_path, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)

                # 设置日志格式
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(formatter)

                # 添加文件处理器
                _repair_info_logger.addHandler(file_handler)
                _repair_info_logger.info(f"Repair Info详细日志已启用，保存到: {_log_file_path}")

                # 同时打印到控制台，确保用户知道日志位置
                print(f"Repair Info详细日志已保存到: {_log_file_path}")

            except Exception as e:
                print(f"创建日志文件失败: {str(e)}")
                # 如果固定路径失败，尝试使用备用路径
                try:
                    backup_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
                    os.makedirs(backup_dir, exist_ok=True)
                    _log_file_path = os.path.join(backup_dir,
                                                  f"repair_info_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

                    file_handler = logging.FileHandler(_log_file_path, encoding='utf-8')
                    file_handler.setLevel(logging.DEBUG)
                    file_handler.setFormatter(formatter)
                    _repair_info_logger.addHandler(file_handler)

                    _repair_info_logger.info(f"使用备用路径保存日志: {_log_file_path}")
                    print(f"使用备用路径保存日志: {_log_file_path}")

                except Exception as e2:
                    print(f"备用路径也失败: {str(e2)}")

        return _repair_info_logger


def _has_file_handler(logger):
    """检查日志记录器是否已经有文件处理器"""
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return True
    return False


def _safe_log_error(logger, message, exc_info=False):
    """安全地记录错误，即使logger为None"""
    if logger is not None:
        if exc_info:
            logger.error(message, exc_info=exc_info)
        else:
            logger.error(message)
    else:
        # 如果logger为None，直接打印到控制台
        print(f"ERROR - {message}")
        if exc_info:
            import traceback
            traceback.print_exc()


def label_method_repair_info(sample, file_path=None):
    """
    根据样本在repair center的维修反馈信息来标注样本状态
    规则：
    1. 先比较样本中的Serial与路径SN是否相同：
       - 如果相同，再看路径的issue种类：
         - 如果是pa_issues，则样本标记为PA abnormal
         - 其它issues，标记为Normal
    2. 如果样本中的Serial与路径SN不相同：
       - 比较样本中的ProductName与路径中的model
         - 如果不相同则标记为Unknown
         - 如果相同，则样本标记为Normal
    """
    try:
        logger = _get_repair_info_logger()
    except Exception as e:
        logger = None
        print(f"获取日志记录器失败: {str(e)}")

    serial = sample['Serial']
    product_name = sample['ProductName']

    try:
        if logger:
            logger.debug(f"开始处理样本 - Serial: {serial}, ProductName: {product_name}")

        if file_path is None:
            # 如果没有提供文件路径，返回Unknown状态
            _safe_log_error(logger, f"未提供文件路径，无法进行repair_info打标 - Serial: {serial}")
            return 'Unknown', 'No file path provided'

        if logger:
            logger.debug(f"文件路径: {file_path}")

        # 解析文件路径
        path_info = _parse_file_path(file_path, logger)
        if not path_info:
            # 如果路径解析失败，返回Unknown状态
            _safe_log_error(logger, f"路径解析失败 - Serial: {serial}, File: {file_path}")
            return 'Unknown', 'Path parsing failed'

        path_sn = path_info['sn']
        issue_type = path_info['issue_type']
        path_model = path_info['model']

        if logger:
            logger.debug(f"路径解析结果 - SN: {path_sn}, Issue Type: {issue_type}, Model: {path_model}")

        # 构建详细信息
        details = f"{issue_type}"

        # 应用新的打标规则
        if serial == path_sn:
            # 规则1: Serial与路径SN相同
            if logger:
                logger.debug(f"Serial匹配 - 样本Serial {serial} 与路径SN {path_sn} 相同")
            if issue_type == 'pa_issues':
                # 规则1.1: 相同且issue类别是pa_issues，标记PA abnormal
                if logger:
                    logger.info(f"判定为PA abnormal - Serial匹配且issue类型为pa_issues")
                pa_status_repair_info = 'PA abnormal'
                details = f"pa_issues"
            else:
                # 规则1.2: 相同但issue类别不是pa_issues，标记为Normal
                if logger:
                    logger.info(f"判定为Normal - Serial匹配但issue类型不是pa_issues: {issue_type}")
                pa_status_repair_info = 'Normal'
                details = f"{issue_type}"
        else:
            # 规则2: Serial与路径SN不相同
            if logger:
                logger.debug(f"Serial不匹配 - 样本Serial {serial} 与路径SN {path_sn} 不同")
            if product_name != path_model:
                # 规则2.1: ProductName与路径model不相同，标记为Unknown
                if logger:
                    logger.info(
                        f"判定为Unknown - Serial不匹配且ProductName {product_name} 与路径Model {path_model} 不同")
                pa_status_repair_info = 'Unknown'
                details = f"unknown"
            else:
                # 规则2.2: ProductName与路径model相同，标记为Normal
                if logger:
                    logger.info(
                        f"判定为Normal - Serial不匹配但ProductName {product_name} 与路径Model {path_model} 相同")
                pa_status_repair_info = 'Normal'
                details = f"{issue_type}"

        # 最终判定结果
        if logger:
            logger.info(f"最终判定 - Serial: {serial}, ProductName: {product_name}, "
                        f"Path SN: {path_sn}, Path Model: {path_model}, "
                        f"Issue Type: {issue_type}, Status: {pa_status_repair_info}")

    except Exception as e:
        _safe_log_error(logger, f"PA Status repair info 判定错误 {serial}: {str(e)}", exc_info=True)
        pa_status_repair_info = 'Unknown'
        details = f"unknown"

    return pa_status_repair_info, details


def _parse_file_path(file_path, logger=None):
    """
    解析文件路径，提取SN号、issue类别和model
    路径格式：.../Platform/Model/xxx_issues/SN/filename.json
    """
    if logger is None:
        try:
            logger = _get_repair_info_logger()
        except:
            logger = None

    try:
        # 检查文件路径是否有效
        if not file_path or not isinstance(file_path, str):
            _safe_log_error(logger, f"文件路径无效: {file_path}")
            return None

        # 获取文件所在目录并规范化路径
        dir_path = os.path.dirname(file_path)
        normalized_path = os.path.normpath(dir_path)
        path_parts = normalized_path.split(os.sep)

        # 过滤掉空字符串
        path_parts = [part for part in path_parts if part]

        if logger:
            logger.debug(f"解析路径: {normalized_path}")
            logger.debug(f"路径分割为 {len(path_parts)} 部分: {path_parts}")

        # 确保路径足够长
        if len(path_parts) < 2:
            _safe_log_error(logger, f"路径格式错误，路径太短: {file_path}")
            return None

        # 从路径末尾开始查找SN、issue_type和model
        sn = None
        issue_type = None
        model = None

        # 从后往前遍历路径部分，查找所需的信息
        for i in range(len(path_parts) - 1, -1, -1):
            part = path_parts[i]

            # 如果还没有找到SN，检查当前部分是否是有效的SN
            if sn is None and _is_valid_sn(part):
                sn = part
                if logger:
                    logger.debug(f"找到SN: {sn}")
                continue

            # 如果已经找到SN但还没有找到issue_type，检查当前部分是否是有效的issue_type
            if sn is not None and issue_type is None and _is_valid_issue_type(part):
                issue_type = part
                if logger:
                    logger.debug(f"找到issue_type: {issue_type}")
                continue

            # 如果已经找到SN和issue_type但还没有找到model，则尝试找到model
            if sn is not None and issue_type is not None and model is None:
                # 查找model（通常在issue_type的前一级）
                if i > 0:
                    model = path_parts[i - 1]
                    if logger:
                        logger.debug(f"找到model: {model}")
                break

        # 如果还没有找到model，尝试从其他位置查找
        if model is None and sn is not None and issue_type is not None:
            # 在路径中查找可能的model（排除SN和issue_type的部分）
            for part in path_parts:
                if part != sn and part != issue_type and part and not _is_valid_sn(
                        part) and not _is_valid_issue_type(part):
                    model = part
                    if logger:
                        logger.debug(f"找到备选model: {model}")
                    break

        # 检查是否成功找到所有必需的信息
        if sn is None:
            _safe_log_error(logger, f"无法在路径中找到有效的SN号: {file_path}")
            return None

        if issue_type is None:
            _safe_log_error(logger, f"无法在路径中找到有效的issue类型: {file_path}")
            return None

        # model不是必需的，如果没有找到可以设为Unknown
        if model is None:
            model = "Unknown"
            if logger:
                logger.warning(f"无法在路径中找到model信息，使用默认值: {model}")

        if logger:
            logger.debug(f"路径解析成功 - SN: {sn}, Issue Type: {issue_type}, Model: {model}")

        return {
            'sn': sn,
            'issue_type': issue_type,
            'model': model,
            'full_path': normalized_path
        }

    except Exception as e:
        _safe_log_error(logger, f"解析文件路径错误 {file_path}: {str(e)}", exc_info=True)
        return None


def _is_valid_sn(sn):
    """
    验证SN号格式
    SN号要求：
    - 总共10位
    - 由字母和数字构成
    - 第一位必须是字母
    """
    if not sn or len(sn) != 10:
        return False

    # 检查第一位是否是字母
    if not sn[0].isalpha():
        return False

    # 检查所有字符是否都是字母或数字
    if not sn.isalnum():
        return False

    return True


def _is_valid_issue_type(issue_type):
    """
    验证issue类型格式
    有效的issue类型包括：
    - pa_issues
    - dcdc_issues
    - digital_issues
    - dpd_issues
    - fu_issues
    - ltu_issues
    - nff_issues
    - sw_issues
    - trx_issues
    """
    valid_issue_types = {
        'pa_issues', 'dcdc_issues', 'digital_issues', 'dpd_issues', 'DPD_issues',
        'fu_issues', 'ltu_issues', 'nff_issues', 'sw_issues', 'trx_issues'
    }

    return issue_type in valid_issue_types
