try:
    from .qiwi import Qiwi
except ImportError:
    pass
from .yoomoney import YooMoney
from .coinbase.bitcoin import Bitcoin
