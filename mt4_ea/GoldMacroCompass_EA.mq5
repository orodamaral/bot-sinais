//+------------------------------------------------------------------+
//|                                               GoldMacroCompass.mq5|
//+------------------------------------------------------------------+
#property copyright "Gold Macro Compass"
#property version   "1.00"

input string Sym_US10Y  = "US10Y";
input string Sym_DXY    = "DXY";
input string Sym_EURUSD = "EURUSD";
input string Sym_USDJPY = "USDJPY";
input string Sym_WTI    = "USOIL";
input string Sym_XAUUSD = "XAUUSD";

input int    MacroTF        = 60;
input int    RegPeriod      = 20;
input int    RSIPeriod      = 7;
input int    RSI_OB         = 80;
input int    RSI_OS         = 20;
input int    EMA_Fast       = 9;
input int    EMA_Slow       = 21;

input double LotSize        = 0.01;
input int    SL_Points      = 500;
input int    TP_Points      = 500;
input int    MaxSpread      = 50;
input int    MinScore       = 3;
input int    MaxTrades      = 1;
input double MaxDailyLoss   = 1000;
input int    MagicNumber    = 202407;

input bool   UseFileSignal  = false;
input string SignalFilePath = "gold_signal.txt";

//+------------------------------------------------------------------+
double g_slope_US10Y, g_slope_DXY, g_slope_EUR, g_slope_JPY, g_slope_WTI;
double g_rsi, g_emaFast, g_emaSlow;
bool   g_emaBull;
int    g_macroScore, g_signal, g_prevSignal = 0;
datetime g_lastCalc = 0;
//+------------------------------------------------------------------+

ENUM_TIMEFRAMES TFM(int m) {
   if(m <= 1) return PERIOD_M1;
   if(m <= 5) return PERIOD_M5;
   if(m <= 15) return PERIOD_M15;
   if(m <= 30) return PERIOD_M30;
   if(m <= 60) return PERIOD_H1;
   if(m <= 240) return PERIOD_H4;
   if(m <= 1440) return PERIOD_D1;
   return PERIOD_H1;
}

datetime T0(string sym, ENUM_TIMEFRAMES tf) {
   datetime b[1]; ArraySetAsSeries(b, true);
   return (CopyTime(sym, tf, 0, 1, b) > 0) ? b[0] : 0;
}

double C(string sym, ENUM_TIMEFRAMES tf, int i) {
   double b[]; ArraySetAsSeries(b, true);
   return (CopyClose(sym, tf, i, 1, b) > 0) ? b[0] : 0;
}

double SL(string sym, ENUM_TIMEFRAMES tf, int len) {
   double b[]; ArraySetAsSeries(b, true);
   int n = CopyClose(sym, tf, 0, len, b);
   if(n < len) return 0;
   double sx=0,sy=0,sxy=0,sx2=0;
   for(int i=0; i<len; i++) {
      double y = b[i]; if(y <= 0) return 0;
      sx+=i; sy+=y; sxy+=i*y; sx2+=i*i;
   }
   double d = len*sx2-sx*sx;
   return (d!=0) ? -(len*sxy-sx*sy)/d : 0;
}

double NS(string sym, ENUM_TIMEFRAMES tf, int len) {
   double s = SL(sym, tf, len);
   double p = C(sym, tf, 0);
   return (p != 0) ? s/p*100.0 : 0;
}

bool SYMOK(string sym) {
   return SymbolSelect(sym, true);
}

//+------------------------------------------------------------------+
void Analysis() {
   ENUM_TIMEFRAMES ct = PERIOD_CURRENT;
   ENUM_TIMEFRAMES mt = TFM(MacroTF);

   datetime cur = T0(Sym_XAUUSD, ct);
   if(cur == 0 || cur == g_lastCalc) return;
   g_lastCalc = cur;

   g_slope_US10Y = NS(Sym_US10Y, mt, RegPeriod);
   g_slope_DXY   = NS(Sym_DXY,   mt, RegPeriod);
   g_slope_EUR   = NS(Sym_EURUSD,mt, RegPeriod);
   g_slope_JPY   = NS(Sym_USDJPY,mt, RegPeriod);
   g_slope_WTI   = NS(Sym_WTI,   mt, RegPeriod);

   bool u10 = g_slope_US10Y>0, dxy=g_slope_DXY>0, eur=g_slope_EUR>0;
   bool jpy=g_slope_JPY>0, wti=g_slope_WTI>0;
   bool bull=!u10, bear=u10;

   g_macroScore = ((bull&&!dxy)||(bear&&dxy)?2:0) + ((dxy&&!eur)||(!dxy&&eur)?1:0)
                + ((bull&&jpy)||(bear&&!jpy)?1:0) + ((u10&&wti)||(!u10&&!wti)?1:0);

   int rh = iRSI(Sym_XAUUSD, ct, RSIPeriod, PRICE_CLOSE);
   double rb[]; ArraySetAsSeries(rb, true);
   if(CopyBuffer(rh, 0, 0, 1, rb) > 0) g_rsi = rb[0];

   int efh = iMA(Sym_XAUUSD, ct, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   int esh = iMA(Sym_XAUUSD, ct, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   double efb[], esb[];
   ArraySetAsSeries(efb, true); ArraySetAsSeries(esb, true);
   if(CopyBuffer(efh, 0, 0, 1, efb) > 0) g_emaFast = efb[0];
   if(CopyBuffer(esh, 0, 0, 1, esb) > 0) g_emaSlow = esb[0];
   g_emaBull = g_emaFast > g_emaSlow;

   bool st = g_macroScore >= 5;
   bool md = g_macroScore >= MinScore && g_macroScore < 5;

   if(bull && st && g_rsi<RSI_OB && g_emaBull)       g_signal = 2;
   else if(bull && md && g_rsi<RSI_OB)                g_signal = 1;
   else if(bear && st && g_rsi>RSI_OS && !g_emaBull)   g_signal = -2;
   else if(bear && md && g_rsi>RSI_OS)                 g_signal = -1;
   else                                                 g_signal = 0;
}

//+------------------------------------------------------------------+
double DLY() {
   datetime d0 = T0(Sym_XAUUSD, PERIOD_D1);
   HistorySelect(d0, TimeCurrent());
   double l=0;
   for(int i=HistoryDealsTotal()-1; i>=0; i--) {
      ulong t = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(t, DEAL_MAGIC) != MagicNumber) continue;
      if((long)HistoryDealGetInteger(t, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      double p = HistoryDealGetDouble(t, DEAL_PROFIT);
      if(p < 0) l += p;
   }
   return MathAbs(l);
}

int CNT() {
   int c=0;
   for(int i=PositionsTotal()-1; i>=0; i--) {
      ulong t = PositionGetTicket(i);
      if(t>0 && PositionSelectByTicket(t))
         if(PositionGetInteger(POSITION_MAGIC)==MagicNumber &&
            PositionGetString(POSITION_SYMBOL)==Sym_XAUUSD) c++;
   }
   return c;
}

bool SPR() {
   return (int)SymbolInfoInteger(Sym_XAUUSD, SYMBOL_SPREAD) <= MaxSpread;
}

//+------------------------------------------------------------------+
void EXEC(int sig) {
   if(!SPR()) { Print("Spread alto"); return; }
   if(DLY() >= MaxDailyLoss) { Print("Max daily loss"); return; }
   if(CNT() >= MaxTrades) return;

   double pt = SymbolInfoDouble(Sym_XAUUSD, SYMBOL_POINT);
   double pr = (sig>0) ? SymbolInfoDouble(Sym_XAUUSD, SYMBOL_ASK)
                       : SymbolInfoDouble(Sym_XAUUSD, SYMBOL_BID);
   double sl = (sig>0) ? pr-SL_Points*pt : pr+SL_Points*pt;
   double tp = (sig>0) ? pr+TP_Points*pt : pr-TP_Points*pt;

   MqlTradeRequest rq={};
   MqlTradeResult rs={};
   rq.action   = TRADE_ACTION_DEAL;
   rq.symbol   = Sym_XAUUSD;
   rq.volume   = LotSize;
   rq.type     = (sig>0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   rq.price    = pr;
   rq.sl       = sl;
   rq.tp       = tp;
   rq.deviation = 20;
   rq.magic    = MagicNumber;
   rq.comment  = "GMC_"+IntegerToString(sig);
   rq.type_filling = ORDER_FILLING_IOC;

   if(OrderSend(rq, rs))
      Print("OK ticket=",rs.order," sig=",sig);
   else
      Print("ERRO cod=",rs.retcode);
}

//+------------------------------------------------------------------+
int OnInit() {
   if(!SYMOK(Sym_XAUUSD)) { Print("ERRO: ", Sym_XAUUSD); return INIT_FAILED; }
   Print("Gold Macro Compass MT5 OK");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int) {}

void OnTick() {
   Analysis();
   if(g_signal != 0 && g_signal != g_prevSignal) { EXEC(g_signal); g_prevSignal = g_signal; }
}

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
