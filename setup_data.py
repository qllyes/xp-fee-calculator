import pandas as pd
import os

def create_store_master():
    data = {
        "门店名称": [f"门店{i}" for i in range(1, 21)],
        "门店类型": ["超级旗舰店"]*2 + ["旗舰店"]*5 + ["标准店"]*8 + ["普通店"]*5,
        "区域": ["华东"]*10 + ["华北"]*10,
        "状态": ["营业中"]*20
    }
    df = pd.DataFrame(data)
    os.makedirs("data", exist_ok=True)
    df.to_excel("data/store_master.xlsx", index=False)
    print("Created data/store_master.xlsx")

def create_batch_template():
    columns = [
        "商品名称", "商品品类", "SKU数", "铺货通道", "预估毛利率(%)", 
        "付款方式", "供应商类型", "进价", "退货条件", 
        "(自定义)超级旗舰店数", "(自定义)旗舰店数", "(自定义)标准店数", "(自定义)普通店数"
    ]
    df = pd.DataFrame(columns=columns)
    # Add a sample row
    sample_row = {
        "商品名称": "示例商品A",
        "商品品类": "护肤",
        "SKU数": 5,
        "铺货通道": "黄色",
        "预估毛利率(%)": 45,
        "付款方式": "月结30天",
        "供应商类型": "经销商",
        "进价": 50,
        "退货条件": "有条件退货",
        "(自定义)超级旗舰店数": None,
        "(自定义)旗舰店数": None,
        "(自定义)标准店数": None,
        "(自定义)普通店数": None
    }
    df = pd.concat([df, pd.DataFrame([sample_row])], ignore_index=True)
    os.makedirs("data", exist_ok=True)
    df.to_excel("data/batch_template.xlsx", index=False)
    print("Created data/batch_template.xlsx")

if __name__ == "__main__":
    create_store_master()
    create_batch_template()
