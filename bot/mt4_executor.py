import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import load_config

logger = logging.getLogger(__name__)

_SIGNAL_FILE = Path(__file__).parent.parent / "data" / "signal.json"
_TRADE_FILE = Path(__file__).parent.parent / "data" / "trade_result.json"
_ORDERS_DIR = Path(__file__).parent.parent / "data" / "orders"


class MT4Executor:
    def __init__(self):
        self.connected = False
        self._init_dirs()

    def _init_dirs(self):
        _SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ORDERS_DIR.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> bool:
        try:
            import MetaTrader4 as mt4
            cfg = load_config()
            mt4_cfg = cfg.get("mt4", {})

            if not mt4.initialize(mt4_cfg.get("path", "")):
                logger.error("Falha ao conectar MT4: %s", mt4.last_error())
                return False

            if mt4_cfg.get("account") and mt4_cfg.get("password"):
                logged = mt4.login(
                    mt4_cfg["account"],
                    mt4_cfg["password"],
                    mt4_cfg.get("server", "")
                )
                if not logged:
                    logger.error("Falha ao logar no MT4: %s", mt4.last_error())
                    return False

            self.connected = True
            logger.info("Conectado ao MT4")
            return True
        except ImportError:
            logger.warning("MetaTrader4 nao instalado. Usando modo arquivo.")
            self.connected = False
            return True
        except Exception as e:
            logger.error("Erro ao conectar MT4: %s", e)
            return False

    def send_signal(self, signal: int, sl_pts: int, tp_pts: int, comment: str = ""):
        sig_data = {
            "timestamp": datetime.now().isoformat(),
            "signal": signal,
            "sl_points": sl_pts,
            "tp_points": tp_pts,
            "comment": comment
        }
        _SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_SIGNAL_FILE, "w") as f:
            json.dump(sig_data, f, indent=2)
        logger.info("Sinal salvo em %s: %d", _SIGNAL_FILE, signal)

        if self.connected:
            self._execute_mt4(signal, sl_pts, tp_pts)

    def _execute_mt4(self, signal: int, sl_pts: int, tp_pts: int):
        import MetaTrader4 as mt4

        cfg = load_config()
        symbol = cfg["macro"]["xauusd_symbol"]

        if not mt4.symbol_select(symbol, True):
            logger.error("Simbolo %s nao disponivel", symbol)
            return

        tick = mt4.symbol_info_tick(symbol)
        if tick is None:
            logger.error("Nao foi possivel obter tick de %s", symbol)
            return

        point = mt4.symbol_info(symbol).point
        if point == 0.0:
            logger.error("Point zero para %s", symbol)
            return

        volume = 0.01
        price = tick.ask if signal > 0 else tick.bid
        sl_price = price - sl_pts * point if signal > 0 else price + sl_pts * point
        tp_price = price + tp_pts * point if signal > 0 else price - tp_pts * point

        order_type = mt4.ORDER_TYPE_BUY if signal > 0 else mt4.ORDER_TYPE_SELL

        request = {
            "action": mt4.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": 20,
            "magic": 202407,
            "comment": "GoldMacroCompass",
            "type_time": mt4.ORDER_TIME_GTC,
            "type_filling": mt4.ORDER_FILLING_IOC,
        }

        result = mt4.order_send(request)
        if result.retcode != mt4.TRADE_RETCODE_DONE:
            logger.error("Ordem falhou: %d - %s", result.retcode, result.comment)
        else:
            logger.info("Ordem executada: ticket %d", result.order)

    def get_trade_result(self) -> Optional[dict]:
        if _TRADE_FILE.exists():
            with open(_TRADE_FILE) as f:
                return json.load(f)
        return None

    def get_balance(self) -> Optional[float]:
        if not self.connected:
            return None
        try:
            import MetaTrader4 as mt4
            account_info = mt4.account_info()
            return account_info.balance if account_info else None
        except Exception:
            return None

    def shutdown(self):
        if self.connected:
            try:
                import MetaTrader4 as mt4
                mt4.shutdown()
                logger.info("MT4 desconectado")
            except Exception:
                pass
