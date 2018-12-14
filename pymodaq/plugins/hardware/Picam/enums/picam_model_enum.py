# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 16:54:14 2018

@author: Weber
"""
from enum import IntEnum

class PicamModelEnum(IntEnum):
    #------------------------------------------------------------------------*/
    # PI-MTE Series (1419) --------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_PIMteSeries              = 1400
    # PI-MTE 1024 Series ----------------------------------------------------*/
    PicamModel_PIMte1024Series          = 1401
    PicamModel_PIMte1024F               = 1402
    PicamModel_PIMte1024B               = 1403
    PicamModel_PIMte1024BR              = 1405
    PicamModel_PIMte1024BUV             = 1404
    # PI-MTE 1024FT Series --------------------------------------------------*/
    PicamModel_PIMte1024FTSeries        = 1406
    PicamModel_PIMte1024FT              = 1407
    PicamModel_PIMte1024BFT             = 1408
    # PI-MTE 1300 Series ----------------------------------------------------*/
    PicamModel_PIMte1300Series          = 1412
    PicamModel_PIMte1300B               = 1413
    PicamModel_PIMte1300R               = 1414
    PicamModel_PIMte1300BR              = 1415
    # PI-MTE 2048 Series ----------------------------------------------------*/
    PicamModel_PIMte2048Series          = 1416
    PicamModel_PIMte2048B               = 1417
    PicamModel_PIMte2048BR              = 1418
    # PI-MTE 2K Series ------------------------------------------------------*/
    PicamModel_PIMte2KSeries            = 1409
    PicamModel_PIMte2KB                 = 1410
    PicamModel_PIMte2KBUV               = 1411
    #------------------------------------------------------------------------*/
    # PIXIS Series (76) -----------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_PixisSeries              =    0
    # PIXIS 100 Series ------------------------------------------------------*/
    PicamModel_Pixis100Series           =    1
    PicamModel_Pixis100F                =    2
    PicamModel_Pixis100B                =    6
    PicamModel_Pixis100R                =    3
    PicamModel_Pixis100C                =    4
    PicamModel_Pixis100BR               =    5
    PicamModel_Pixis100BExcelon         =   54
    PicamModel_Pixis100BRExcelon        =   55
    PicamModel_PixisXO100B              =    7
    PicamModel_PixisXO100BR             =    8
    PicamModel_PixisXB100B              =   68
    PicamModel_PixisXB100BR             =   69
    # PIXIS 256 Series ------------------------------------------------------*/
    PicamModel_Pixis256Series           =   26
    PicamModel_Pixis256F                =   27
    PicamModel_Pixis256B                =   29
    PicamModel_Pixis256E                =   28
    PicamModel_Pixis256BR               =   30
    PicamModel_PixisXB256BR             =   31
    # PIXIS 400 Series ------------------------------------------------------*/
    PicamModel_Pixis400Series           =   37
    PicamModel_Pixis400F                =   38
    PicamModel_Pixis400B                =   40
    PicamModel_Pixis400R                =   39
    PicamModel_Pixis400BR               =   41
    PicamModel_Pixis400BExcelon         =   56
    PicamModel_Pixis400BRExcelon        =   57
    PicamModel_PixisXO400B              =   42
    PicamModel_PixisXB400BR             =   70
    # PIXIS 512 Series ------------------------------------------------------*/
    PicamModel_Pixis512Series           =   43
    PicamModel_Pixis512F                =   44
    PicamModel_Pixis512B                =   45
    PicamModel_Pixis512BUV              =   46
    PicamModel_Pixis512BExcelon         =   58
    PicamModel_PixisXO512F              =   49
    PicamModel_PixisXO512B              =   50
    PicamModel_PixisXF512F              =   48
    PicamModel_PixisXF512B              =   47
    # PIXIS 1024 Series -----------------------------------------------------*/
    PicamModel_Pixis1024Series          =    9
    PicamModel_Pixis1024F               =   10
    PicamModel_Pixis1024B               =   11
    PicamModel_Pixis1024BR              =   13
    PicamModel_Pixis1024BUV             =   12
    PicamModel_Pixis1024BExcelon        =   59
    PicamModel_Pixis1024BRExcelon       =   60
    PicamModel_PixisXO1024F             =   16
    PicamModel_PixisXO1024B             =   14
    PicamModel_PixisXO1024BR            =   15
    PicamModel_PixisXF1024F             =   17
    PicamModel_PixisXF1024B             =   18
    PicamModel_PixisXB1024BR            =   71
    # PIXIS 1300 Series -----------------------------------------------------*/
    PicamModel_Pixis1300Series          =   51
    PicamModel_Pixis1300F               =   52
    PicamModel_Pixis1300F_2             =   75
    PicamModel_Pixis1300B               =   53
    PicamModel_Pixis1300BR              =   73
    PicamModel_Pixis1300BExcelon        =   61
    PicamModel_Pixis1300BRExcelon       =   62
    PicamModel_PixisXO1300B             =   65
    PicamModel_PixisXF1300B             =   66
    PicamModel_PixisXB1300R             =   72
    # PIXIS 2048 Series -----------------------------------------------------*/
    PicamModel_Pixis2048Series          =   20
    PicamModel_Pixis2048F               =   21
    PicamModel_Pixis2048B               =   22
    PicamModel_Pixis2048BR              =   67
    PicamModel_Pixis2048BExcelon        =   63
    PicamModel_Pixis2048BRExcelon       =   74
    PicamModel_PixisXO2048B             =   23
    PicamModel_PixisXF2048F             =   25
    PicamModel_PixisXF2048B             =   24
    # PIXIS 2K Series -------------------------------------------------------*/
    PicamModel_Pixis2KSeries            =   32
    PicamModel_Pixis2KF                 =   33
    PicamModel_Pixis2KB                 =   34
    PicamModel_Pixis2KBUV               =   36
    PicamModel_Pixis2KBExcelon          =   64
    PicamModel_PixisXO2KB               =   35
    #------------------------------------------------------------------------*/
    # Quad-RO Series (104) --------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_QuadroSeries             =  100
    PicamModel_Quadro4096               =  101
    PicamModel_Quadro4096_2             =  103
    PicamModel_Quadro4320               =  102
    #------------------------------------------------------------------------*/
    # ProEM Series (214) ----------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_ProEMSeries              =  200
    # ProEM 512 Series ------------------------------------------------------*/
    PicamModel_ProEM512Series           =  203
    PicamModel_ProEM512B                =  201
    PicamModel_ProEM512BK               =  205
    PicamModel_ProEM512BExcelon         =  204
    PicamModel_ProEM512BKExcelon        =  206
    # ProEM 1024 Series -----------------------------------------------------*/
    PicamModel_ProEM1024Series          =  207
    PicamModel_ProEM1024B               =  202
    PicamModel_ProEM1024BExcelon        =  208
    # ProEM 1600 Series -----------------------------------------------------*/
    PicamModel_ProEM1600Series          =  209
    PicamModel_ProEM1600xx2B            =  212
    PicamModel_ProEM1600xx2BExcelon     =  210
    PicamModel_ProEM1600xx4B            =  213
    PicamModel_ProEM1600xx4BExcelon     =  211
    #------------------------------------------------------------------------*/
    # ProEM+ Series (614) ---------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_ProEMPlusSeries          =  600
    # ProEM+ 512 Series -----------------------------------------------------*/
    PicamModel_ProEMPlus512Series       =  603
    PicamModel_ProEMPlus512B            =  601
    PicamModel_ProEMPlus512BK           =  605
    PicamModel_ProEMPlus512BExcelon     =  604
    PicamModel_ProEMPlus512BKExcelon    =  606
    # ProEM+ 1024 Series ----------------------------------------------------*/
    PicamModel_ProEMPlus1024Series      =  607
    PicamModel_ProEMPlus1024B           =  602
    PicamModel_ProEMPlus1024BExcelon    =  608
    # ProEM+ 1600 Series ----------------------------------------------------*/
    PicamModel_ProEMPlus1600Series      =  609
    PicamModel_ProEMPlus1600xx2B        =  612
    PicamModel_ProEMPlus1600xx2BExcelon =  610
    PicamModel_ProEMPlus1600xx4B        =  613
    PicamModel_ProEMPlus1600xx4BExcelon =  611
    #------------------------------------------------------------------------*/
    # ProEM-HS Series (1216) ------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_ProEMHSSeries            = 1200
    # ProEM-HS 512 Series ---------------------------------------------------*/
    PicamModel_ProEMHS512Series         = 1201
    PicamModel_ProEMHS512B              = 1202
    PicamModel_ProEMHS512BK             = 1207
    PicamModel_ProEMHS512BExcelon       = 1203
    PicamModel_ProEMHS512BKExcelon      = 1208
    # ProEM-HS 1024 Series --------------------------------------------------*/
    PicamModel_ProEMHS1024Series        = 1204
    PicamModel_ProEMHS1024B             = 1205
    PicamModel_ProEMHS1024BExcelon      = 1206
    PicamModel_ProEMHS1024B_2           = 1212
    PicamModel_ProEMHS1024BExcelon_2    = 1213
    PicamModel_ProEMHS1024B_3           = 1214
    PicamModel_ProEMHS1024BExcelon_3    = 1215
    # ProEM-HS 1K-10 Series -------------------------------------------------*/
    PicamModel_ProEMHS1K10Series        = 1209
    PicamModel_ProEMHS1KB10             = 1210
    PicamModel_ProEMHS1KB10Excelon      = 1211
    #------------------------------------------------------------------------*/
    # PI-MAX3 Series (303) --------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_PIMax3Series             =  300
    PicamModel_PIMax31024I              =  301
    PicamModel_PIMax31024x256           =  302
    #------------------------------------------------------------------------*/
    # PI-MAX4 Series (721) --------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_PIMax4Series             =  700
    # PI-MAX4 1024i Series --------------------------------------------------*/
    PicamModel_PIMax41024ISeries        =  703
    PicamModel_PIMax41024I              =  701
    PicamModel_PIMax41024IRF            =  704
    # PI-MAX4 1024f Series --------------------------------------------------*/
    PicamModel_PIMax41024FSeries        =  710
    PicamModel_PIMax41024F              =  711
    PicamModel_PIMax41024FRF            =  712
    # PI-MAX4 1024x256 Series -----------------------------------------------*/
    PicamModel_PIMax41024x256Series     =  705
    PicamModel_PIMax41024x256           =  702
    PicamModel_PIMax41024x256RF         =  706
    # PI-MAX4 2048 Series ---------------------------------------------------*/
    PicamModel_PIMax42048Series         =  716
    PicamModel_PIMax42048F              =  717
    PicamModel_PIMax42048B              =  718
    PicamModel_PIMax42048FRF            =  719
    PicamModel_PIMax42048BRF            =  720
    # PI-MAX4 512EM Series --------------------------------------------------*/
    PicamModel_PIMax4512EMSeries        =  708
    PicamModel_PIMax4512EM              =  707
    PicamModel_PIMax4512BEM             =  709
    # PI-MAX4 1024EM Series -------------------------------------------------*/
    PicamModel_PIMax41024EMSeries       =  713
    PicamModel_PIMax41024EM             =  715
    PicamModel_PIMax41024BEM            =  714
    #------------------------------------------------------------------------*/
    # PyLoN Series (439) ----------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_PylonSeries              =  400
    # PyLoN 100 Series ------------------------------------------------------*/
    PicamModel_Pylon100Series           =  418
    PicamModel_Pylon100F                =  404
    PicamModel_Pylon100B                =  401
    PicamModel_Pylon100BR               =  407
    PicamModel_Pylon100BExcelon         =  425
    PicamModel_Pylon100BRExcelon        =  426
    # PyLoN 256 Series ------------------------------------------------------*/
    PicamModel_Pylon256Series           =  419
    PicamModel_Pylon256F                =  409
    PicamModel_Pylon256B                =  410
    PicamModel_Pylon256E                =  411
    PicamModel_Pylon256BR               =  412
    # PyLoN 400 Series ------------------------------------------------------*/
    PicamModel_Pylon400Series           =  420
    PicamModel_Pylon400F                =  405
    PicamModel_Pylon400B                =  402
    PicamModel_Pylon400BR               =  408
    PicamModel_Pylon400BExcelon         =  427
    PicamModel_Pylon400BRExcelon        =  428
    # PyLoN 1024 Series -----------------------------------------------------*/
    PicamModel_Pylon1024Series          =  421
    PicamModel_Pylon1024B               =  417
    PicamModel_Pylon1024BExcelon        =  429
    # PyLoN 1300 Series -----------------------------------------------------*/
    PicamModel_Pylon1300Series          =  422
    PicamModel_Pylon1300F               =  406
    PicamModel_Pylon1300B               =  403
    PicamModel_Pylon1300R               =  438
    PicamModel_Pylon1300BR              =  432
    PicamModel_Pylon1300BExcelon        =  430
    PicamModel_Pylon1300BRExcelon       =  433
    # PyLoN 2048 Series -----------------------------------------------------*/
    PicamModel_Pylon2048Series          =  423
    PicamModel_Pylon2048F               =  415
    PicamModel_Pylon2048B               =  434
    PicamModel_Pylon2048BR              =  416
    PicamModel_Pylon2048BExcelon        =  435
    PicamModel_Pylon2048BRExcelon       =  436
    # PyLoN 2K Series -------------------------------------------------------*/
    PicamModel_Pylon2KSeries            =  424
    PicamModel_Pylon2KF                 =  413
    PicamModel_Pylon2KB                 =  414
    PicamModel_Pylon2KBUV               =  437
    PicamModel_Pylon2KBExcelon          =  431
    #------------------------------------------------------------------------*/
    # PyLoN-IR Series (904) -------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_PylonirSeries            =  900
    # PyLoN-IR 1024 Series --------------------------------------------------*/
    PicamModel_Pylonir1024Series        =  901
    PicamModel_Pylonir102422            =  902
    PicamModel_Pylonir102417            =  903
    #------------------------------------------------------------------------*/
    # PIoNIR Series (502) ---------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_PionirSeries             =  500
    PicamModel_Pionir640                =  501
    #------------------------------------------------------------------------*/
    # NIRvana Series (802) --------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_NirvanaSeries            =  800
    PicamModel_Nirvana640               =  801
    #------------------------------------------------------------------------*/
    # NIRvana ST Series (1302) ----------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_NirvanaSTSeries          = 1300
    PicamModel_NirvanaST640             = 1301
    #------------------------------------------------------------------------*/
    # NIRvana-LN Series (1102) ----------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_NirvanaLNSeries          = 1100
    PicamModel_NirvanaLN640             = 1101
    #------------------------------------------------------------------------*/
    # SOPHIA Series (1843) --------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_SophiaSeries             = 1800
    # SOPHIA 2048 Series ----------------------------------------------------*/
    PicamModel_Sophia2048Series         = 1801
    PicamModel_Sophia2048B              = 1802
    PicamModel_Sophia2048BExcelon       = 1803
    PicamModel_SophiaXO2048B            = 1804
    PicamModel_SophiaXF2048B            = 1805
    PicamModel_SophiaXB2048B            = 1806
    # SOPHIA 2048-13.5 Series -----------------------------------------------*/
    PicamModel_Sophia2048135Series      = 1807
    PicamModel_Sophia2048135            = 1808
    PicamModel_Sophia2048B135           = 1809
    PicamModel_Sophia2048BR135          = 1810
    PicamModel_Sophia2048B135Excelon    = 1811
    PicamModel_Sophia2048BR135Excelon   = 1812
    PicamModel_SophiaXO2048B135         = 1813
    PicamModel_SophiaXO2048BR135        = 1814
    #------------------------------------------------------------------------*/
    # BLAZE Series (1519) ---------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_BlazeSeries              = 1500
    # BLAZE 100 Series ------------------------------------------------------*/
    PicamModel_Blaze100Series           = 1507
    PicamModel_Blaze100B                = 1501
    PicamModel_Blaze100BR               = 1505
    PicamModel_Blaze100HR               = 1503
    PicamModel_Blaze100BRLD             = 1509
    PicamModel_Blaze100BExcelon         = 1511
    PicamModel_Blaze100BRExcelon        = 1513
    PicamModel_Blaze100HRExcelon        = 1515
    PicamModel_Blaze100BRLDExcelon      = 1517
    # BLAZE 400 Series ------------------------------------------------------*/
    PicamModel_Blaze400Series           = 1508
    PicamModel_Blaze400B                = 1502
    PicamModel_Blaze400BR               = 1506
    PicamModel_Blaze400HR               = 1504
    PicamModel_Blaze400BRLD             = 1510
    PicamModel_Blaze400BExcelon         = 1512
    PicamModel_Blaze400BRExcelon        = 1514
    PicamModel_Blaze400HRExcelon        = 1516
    PicamModel_Blaze400BRLDExcelon      = 1518
    #------------------------------------------------------------------------*/
    # FERGIE Series (1612) --------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_FergieSeries             = 1600
    # FERGIE 256 Series -----------------------------------------------------*/
    PicamModel_Fergie256Series          = 1601
    PicamModel_Fergie256B               = 1602
    PicamModel_Fergie256BR              = 1607
    PicamModel_Fergie256BExcelon        = 1603
    PicamModel_Fergie256BRExcelon       = 1608
    # FERGIE 256FT Series ---------------------------------------------------*/
    PicamModel_Fergie256FTSeries        = 1604
    PicamModel_Fergie256FFT             = 1609
    PicamModel_Fergie256BFT             = 1605
    PicamModel_Fergie256BRFT            = 1610
    PicamModel_Fergie256BFTExcelon      = 1606
    PicamModel_Fergie256BRFTExcelon     = 1611
    #------------------------------------------------------------------------*/
    # FERGIE Accessory Series (1706) ----------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_FergieAccessorySeries    = 1700
    # FERGIE Lamp Series ----------------------------------------------------*/
    PicamModel_FergieLampSeries         = 1701
    PicamModel_FergieAEL                = 1702
    PicamModel_FergieQTH                = 1703
    # FERGIE Laser Series ---------------------------------------------------*/
    PicamModel_FergieLaserSeries        = 1704
    PicamModel_FergieLaser785           = 1705
    #------------------------------------------------------------------------*/
    # KURO Series (1904) ----------------------------------------------------*/
    #------------------------------------------------------------------------*/
    PicamModel_KuroSeries               = 1900
    PicamModel_Kuro1200B                = 1901
    PicamModel_Kuro1608B                = 1902
    PicamModel_Kuro2048B                = 1903
    #------------------------------------------------------------------------*/
    def names(self):
        return [name for name, member in self.__members__.items()]