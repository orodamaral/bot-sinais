//+------------------------------------------------------------------+
//|                                                    GoldMacroCompass|
//+------------------------------------------------------------------+
#property copyright "Gold Macro Compass"
#property version   "1.00"
#property strict

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
input string SignalFilePath = "gold_signal.json";

//+------------------------------------------------------------------+
double g_slope_US10Y, g_slope_DXY, g_slope_EUR, g_slope_JPY, g_slope_WTI;
double g_rsi, g_emaFast, g_emaSlow;
bool   g_emaBull;
int    g_macroScore, g_signal;
int    g_prevSignal = 0;
datetime g_lastCalc = 0;
//+------------------------------------------------------------------+

double LinRegSlope(string sym, int tf, int len) {
   double sx=0, sy=0, sxy=0, sx2=0;
   for(int i=0; i<len; i++) {
      double y = iClose(sym, tf, i);
      if(y <= 0) return 0;
      sx += i;
      sy += y;
      sxy += i*y;
      sx2 += i*i;
   }
   double n = len;
   double num = n*sxy - sx*sy;
   double den = n*sx2 - sx*sx;
   return (den != 0) ? -num/den : 0;
}

double NormSlope(string sym, int tf, int len) {
   double s = LinRegSlope(sym, tf, len);
   double price = iClose(sym, tf, 0);
   return (price != 0) ? s/price*100.0 : 0;
}

//+------------------------------------------------------------------+
bool SymbolAvailable(string sym) {
   for(int i=0; i<SymbolsTotal(true); i++) {
      if(SymbolName(i, true) == sym) return true;
   }
   return false;
}

//+------------------------------------------------------------------+
void RefreshAnalysis() {
   if(Time[0] == g_lastCalc) return;
   g_lastCalc = Time[0];

   int tf = MacroTF;

   g_slope_US10Y = NormSlope(Sym_US10Y, tf, RegPeriod);
   g_slope_DXY   = NormSlope(Sym_DXY,   tf, RegPeriod);
   g_slope_EUR   = NormSlope(Sym_EURUSD, tf, RegPeriod);
   g_slope_JPY   = NormSlope(Sym_USDJPY, tf, RegPeriod);
   g_slope_WTI   = NormSlope(Sym_WTI,   tf, RegPeriod);

   bool us10yUp = g_slope_US10Y > 0;
   bool dxyUp   = g_slope_DXY > 0;
   bool eurUp   = g_slope_EUR > 0;
   bool jpyUp   = g_slope_JPY > 0;
   bool wtiUp   = g_slope_WTI > 0;

   bool macroBull = !us10yUp;
   bool macroBear = us10yUp;

   bool dxyConf = (macroBull && !dxyUp) || (macroBear && dxyUp);
   bool eurConf = (dxyUp && !eurUp) || (!dxyUp && eurUp);
   bool jpyAlign = (macroBull && jpyUp) || (macroBear && !jpyUp);
   bool wtiAlign = (us10yUp && wtiUp) || (!us10yUp && !wtiUp);

   g_macroScore = (dxyConf ? 2:0) + (eurConf ? 1:0) + (jpyAlign ? 1:0) + (wtiAlign ? 1:0);

   g_rsi = iRSI(Sym_XAUUSD, PERIOD_CURRENT, RSIPeriod, PRICE_CLOSE, 0);
   g_emaFast = iMA(Sym_XAUUSD, PERIOD_CURRENT, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE, 0);
   g_emaSlow = iMA(Sym_XAUUSD, PERIOD_CURRENT, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE, 0);
   g_emaBull = g_emaFast > g_emaSlow;

   bool macroStrong = g_macroScore >= 5;
   bool macroMod    = g_macroScore >= MinScore && g_macroScore < 5;

   if(macroBull && macroStrong && g_rsi < RSI_OB && g_emaBull)
      g_signal = 2;
   else if(macroBull && macroMod && g_rsi < RSI_OB)
      g_signal = 1;
   else if(macroBear && macroStrong && g_rsi > RSI_OS && !g_emaBull)
      g_signal = -2;
   else if(macroBear && macroMod && g_rsi > RSI_OS)
      g_signal = -1;
   else
      g_signal = 0;
}

//+------------------------------------------------------------------+
bool CheckSpread() {
   return ((Ask - Bid) / Point) <= MaxSpread;
}

double CalcDailyLoss() {
   double loss = 0;
   datetime todayStart = iTime(Sym_XAUUSD, PERIOD_D1, 0);
   for(int i=OrdersHistoryTotal()-1; i>=0; i--) {
      if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) {
         if(OrderMagicNumber() != MagicNumber) continue;
         if(OrderCloseTime() < todayStart) break;
         if(OrderProfit() < 0) loss += OrderProfit();
      }
   }
   return MathAbs(loss);
}

int CountOpenTrades() {
   int count = 0;
   for(int i=OrdersTotal()-1; i>=0; i--) {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) {
         if(OrderMagicNumber() == MagicNumber && OrderSymbol() == Sym_XAUUSD)
            count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
void ExecuteSignal(int sig) {
   if(!CheckSpread()) {
      Print("Spread alto demais: ", (Ask-Bid)/Point);
      return;
   }
   if(CalcDailyLoss() >= MaxDailyLoss) {
      Print("Perda diaria maxima atingida (", CalcDailyLoss(), "/", MaxDailyLoss, ")");
      return;
   }
   if(CountOpenTrades() >= MaxTrades) {
      return;
   }

   double price = (sig > 0) ? Ask : Bid;
   double sl, tp;

   if(sig > 0) {
      sl = price - SL_Points * Point;
      tp = price + TP_Points * Point;
   } else {
      sl = price + SL_Points * Point;
      tp = price - TP_Points * Point;
   }

   int cmd = (sig > 0) ? OP_BUY : OP_SELL;
   string cmt = "GMC_" + IntegerToString(sig);

   int ticket = OrderSend(Sym_XAUUSD, cmd, LotSize, price, 20, sl, tp, cmt, MagicNumber, 0, clrNONE);
   if(ticket < 0) {
      Print("Erro ordem: ", GetLastError());
   } else {
      Print("Ordem OK: ticket ", ticket, " sinal=", sig);
   }
}

//+------------------------------------------------------------------+
void ReadSignalFile() {
   if(!UseFileSignal) return;

   string folder = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL4\\Files\\";
   string path = folder + SignalFilePath;
   int h = FileOpen(path, FILE_READ|FILE_TXT, ',');
   if(h == INVALID_HANDLE) return;

   string sigStr = FileReadString(h);
   FileClose(h);

   int sig = (int)StringToInteger(sigStr);
   if(sig != 0 && sig != g_prevSignal) {
      ExecuteSignal(sig);
      g_prevSignal = sig;
   }
}

//+------------------------------------------------------------------+
int OnInit() {
   if(!SymbolAvailable(Sym_XAUUSD)) {
      Print("ERRO: ", Sym_XAUUSD, " nao encontrado");
      return INIT_FAILED;
   }
   Print("Gold Macro Compass EA iniciado");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   Print("Gold Macro Compass EA finalizado");
}

void OnTick() {
   RefreshAnalysis();

   if(g_signal != 0 && g_signal != g_prevSignal) {
      ExecuteSignal(g_signal);
      g_prevSignal = g_signal;
   }

   if(UseFileSignal) ReadSignalFile();
}
//+------------------------------------------------------------------+
