import pytest
from src.core.calculator import calculate_fee
from src.core.config_loader import load_config

@pytest.fixture
def config():
    return load_config("config/coefficients.yaml")

def test_calculate_fee_basic(config):
    row_data = {
        "商品品类": "护肤",
        "SKU数": 3, # Discount 1.0
        "预估毛利率(%)": 40, # Coeff 1.0
        "付款方式": "月结30天", # Coeff 1.0
        "进价": 5, # Coeff 1.0
        "退货条件": "有条件退货", # Coeff 1.0
        "供应商类型": "经销商" # Coeff 1.0
    }
    
    # 10 Super Flagship * 500 = 5000
    store_counts = {"超级旗舰店": 10}
    
    result = calculate_fee(row_data, store_counts, config)
    
    assert result["final_fee"] == 5000
    assert "基础费用合计: 5000元" in result["breakdown_str"]

def test_calculate_fee_min_floor(config):
    row_data = {
        "商品品类": "护肤",
        "SKU数": 3,
        "预估毛利率(%)": 40,
        "付款方式": "月结30天",
        "进价": 5,
        "退货条件": "有条件退货",
        "供应商类型": "经销商"
    }
    
    # 1 Standard Store * 150 = 150
    # Min floor for Skincare is 1000
    store_counts = {"标准店": 1}
    
    result = calculate_fee(row_data, store_counts, config)
    
    assert result["final_fee"] == 1000
    assert "触发最低兜底" in result["breakdown_str"]
