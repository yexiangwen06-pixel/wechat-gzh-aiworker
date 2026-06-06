import json


BUILTIN_TEMPLATES = [
    {
        "id": 1,
        "name": "新品上市模板",
        "content_type": "new_product",
        "style_name": "专业科技风",
        "outline": json.dumps(
            ["痛点场景", "产品亮点", "核心技术", "适用场景", "行动召唤"],
            ensure_ascii=False,
        ),
        "html_style": "blue_tech",
        "cta_style": "预约企业饮水方案咨询",
    },
    {
        "id": 2,
        "name": "节日促销模板",
        "content_type": "holiday_campaign",
        "style_name": "促销活动风",
        "outline": json.dumps(
            ["节日场景", "优惠信息", "推荐方案", "截止提醒", "行动召唤"],
            ensure_ascii=False,
        ),
        "html_style": "campaign",
        "cta_style": "联系顾问领取活动方案",
    },
    {
        "id": 3,
        "name": "简洁品牌模板",
        "content_type": "new_product",
        "style_name": "简洁品牌风",
        "outline": json.dumps(
            ["品牌引入", "核心信息", "用户价值", "行动召唤"],
            ensure_ascii=False,
        ),
        "html_style": "clean_brand",
        "cta_style": "了解更多企业饮水服务",
    },
]
