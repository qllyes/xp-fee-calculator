import pandas as pd
import io
import tempfile
import os

def read_excel_safe(file_path_or_buffer, dtype_spec=None, **kwargs) -> pd.DataFrame:
    """
    安全的Excel读取方法 (移植自 xp-analysis-map)。
    通过保存为临时文件来解决某些加密或流式读取的问题。
    """
    # 将传入的文件或缓冲区统一转换为BytesIO对象
    if hasattr(file_path_or_buffer, 'getvalue'):
        buffer = io.BytesIO(file_path_or_buffer.getvalue())
        file_name = getattr(file_path_or_buffer, 'name', 'in-memory-file')
    else:
        with open(file_path_or_buffer, 'rb') as f:
            buffer = io.BytesIO(f.read())
        file_name = str(file_path_or_buffer)

    # 创建一个带.xlsx后缀的临时文件
    # delete=False 确保文件在关闭后仍然存在，以便 pandas 读取
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        temp_file_path = temp_file.name
        buffer.seek(0)
        temp_file.write(buffer.read())

    try:
        # 尝试使用不同的引擎读取
        # 优先使用 openpyxl (支持 .xlsx), 备选 xlrd (支持 .xls)
        engines = ['openpyxl', 'xlrd']
        last_exception = None
        
        for engine in engines:
            try:
                # 在读取时传入dtype参数
                return pd.read_excel(temp_file_path, engine=engine, dtype=dtype_spec, **kwargs)
            except Exception as e:
                last_exception = e
                continue
        
        # 如果所有引擎都失败了
        raise ValueError(f"无法使用任何可用引擎读取文件 '{file_name}'。错误: {last_exception}")
        
    finally:
        # 确保临时文件被删除
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except Exception as cleanup_e:
            print(f"Warning: 清理临时文件 '{temp_file_path}' 失败: {cleanup_e}")
