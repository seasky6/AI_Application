import os


def get_output_files_path(create_if_missing: bool = True) -> str:
    """
    获取工程中的 output_files 路径。

    Args:
        create_if_missing (bool): 如果目录不存在，是否自动创建。默认创建。

    Returns:
        str: output_files 的绝对路径
    """
    # 获取当前文件所在路径（推荐在主入口文件中使用）
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 如果你的项目结构中 output_files 是放在项目根目录下
    project_root = base_dir
    while not os.path.exists(os.path.join(project_root, 'input_files')) and project_root != os.path.dirname(
            project_root):
        project_root = os.path.dirname(project_root)

    output_path = os.path.join(project_root, 'input_files')

    if create_if_missing and not os.path.exists(output_path):
        os.makedirs(output_path)

    return output_path
