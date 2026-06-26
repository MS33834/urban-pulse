"""
地区配置模块
"""

from config.regions.beijing import BeijingConfig
from config.regions.changchun import ChangchunConfig
from config.regions.changsha import ChangshaConfig
from config.regions.chengdu import ChengduConfig
from config.regions.chongqing import ChongqingConfig
from config.regions.dalian import DalianConfig
from config.regions.dongguan import DongguanConfig
from config.regions.foshan import FoshanConfig
from config.regions.fuzhou import FuzhouConfig
from config.regions.guangzhou import GuangzhouConfig
from config.regions.guiyang import GuiyangConfig
from config.regions.hangzhou import HangzhouConfig
from config.regions.harbin import HarbinConfig
from config.regions.hefei import HefeiConfig
from config.regions.jinan import JinanConfig
from config.regions.kunming import KunmingConfig
from config.regions.lanzhou import LanzhouConfig
from config.regions.nanchang import NanchangConfig
from config.regions.nanjing import NanjingConfig
from config.regions.nanning import NanningConfig
from config.regions.ningbo import NingboConfig
from config.regions.qingdao import QingdaoConfig
from config.regions.shanghai import ShanghaiConfig
from config.regions.shenyang import ShenyangConfig
from config.regions.shenzhen import ShenzhenConfig
from config.regions.shijiazhuang import ShijiazhuangConfig
from config.regions.suzhou import SuzhouConfig
from config.regions.taiyuan import TaiyuanConfig
from config.regions.tianjin import TianjinConfig
from config.regions.urumqi import UrumqiConfig
from config.regions.wuhan import WuhanConfig
from config.regions.wuxi import WuxiConfig
from config.regions.xiamen import XiamenConfig
from config.regions.xian import XianConfig
from config.regions.zhengzhou import ZhengzhouConfig

REGION_CONFIG_MAP = {
    "深圳": ShenzhenConfig,
    "上海": ShanghaiConfig,
    "北京": BeijingConfig,
    "广州": GuangzhouConfig,
    "苏州": SuzhouConfig,
    "成都": ChengduConfig,
    "杭州": HangzhouConfig,
    "武汉": WuhanConfig,
    "南京": NanjingConfig,
    "西安": XianConfig,
    "重庆": ChongqingConfig,
    "天津": TianjinConfig,
    "青岛": QingdaoConfig,
    "宁波": NingboConfig,
    "无锡": WuxiConfig,
    "长沙": ChangshaConfig,
    "郑州": ZhengzhouConfig,
    "佛山": FoshanConfig,
    "济南": JinanConfig,
    "合肥": HefeiConfig,
    "福州": FuzhouConfig,
    "厦门": XiamenConfig,
    "东莞": DongguanConfig,
    "昆明": KunmingConfig,
    "沈阳": ShenyangConfig,
    "大连": DalianConfig,
    "哈尔滨": HarbinConfig,
    "长春": ChangchunConfig,
    "石家庄": ShijiazhuangConfig,
    "太原": TaiyuanConfig,
    "南昌": NanchangConfig,
    "贵阳": GuiyangConfig,
    "南宁": NanningConfig,
    "乌鲁木齐": UrumqiConfig,
    "兰州": LanzhouConfig,
}


def get_region_config(name: str):
    return REGION_CONFIG_MAP.get(name)


def list_all_regions():
    return list(REGION_CONFIG_MAP.keys())


__all__ = [
    "ShenzhenConfig",
    "ShanghaiConfig",
    "BeijingConfig",
    "GuangzhouConfig",
    "SuzhouConfig",
    "ChengduConfig",
    "HangzhouConfig",
    "WuhanConfig",
    "NanjingConfig",
    "XianConfig",
    "ChongqingConfig",
    "TianjinConfig",
    "QingdaoConfig",
    "NingboConfig",
    "WuxiConfig",
    "ChangshaConfig",
    "ZhengzhouConfig",
    "FoshanConfig",
    "JinanConfig",
    "HefeiConfig",
    "FuzhouConfig",
    "XiamenConfig",
    "DongguanConfig",
    "KunmingConfig",
    "ShenyangConfig",
    "DalianConfig",
    "HarbinConfig",
    "ChangchunConfig",
    "ShijiazhuangConfig",
    "TaiyuanConfig",
    "NanchangConfig",
    "GuiyangConfig",
    "NanningConfig",
    "UrumqiConfig",
    "LanzhouConfig",
    "REGION_CONFIG_MAP",
    "get_region_config",
    "list_all_regions",
]
