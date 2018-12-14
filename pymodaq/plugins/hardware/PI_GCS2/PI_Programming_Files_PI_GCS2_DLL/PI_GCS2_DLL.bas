Attribute VB_Name = "MPI_GCS2"
'/////////////////////////////////////////////////////////////////////////////
'// This is a part of the PI-Software Sources
'// Copyright (C) 1995-2002 PHYSIK INSTRUMENTE GmbH
'// All rights reserved.
'//

'/////////////////////////////////////////////////////////////////////////////
'// Program: PI_G-Control DLL
'//
'// Developer: JKa
'//
'// File: PI_GCS_DLL.h :
'/////////////////////////////////////////////////////////////////////////////

'//#include <windows.h>
'//#include "stdwx.h"










'////////////////////////////////
'// E-7XX Bits (PI_BIT_XXX). //
'////////////////////////////////








'/////////////////////////////////////////////////////////////////////////////
'// DLL initialization and comm functions
Public Declare Function PI_InterfaceSetupDlg Lib "PI_GCS2_DLL.dll" (ByVal szRegKeyName As String) As Long
Public Declare Function PI_ConnectRS232 Lib "PI_GCS2_DLL.dll" (ByVal nPortNr As Long, ByVal nBaudRate As Long) As Long
Public Declare Function PI_ConnectRS232ByDevName Lib "PI_GCS2_DLL.dll" (ByVal szDevName As String, ByVal BaudRate As Long) As Long
Public Declare Function PI_OpenRS232DaisyChain Lib "PI_GCS2_DLL.dll" (ByVal iPortNumber As Long, ByVal iBaudRate As Long, ByRef pNumberOfConnectedDaisyChainDevices As Long, ByVal szDeviceIDNs As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_ConnectDaisyChainDevice Lib "PI_GCS2_DLL.dll" (ByVal iPortId As Long, ByVal iDeviceNumber As Long) As Long
Public Declare Sub PI_CloseDaisyChain Lib "PI_GCS2_DLL.dll" (ByVal iPortId As Long)

Public Declare Function PI_ConnectNIgpib Lib "PI_GCS2_DLL.dll" (ByVal nBoard As Long, ByVal nDevAddr As Long) As Long

Public Declare Function PI_ConnectTCPIP Lib "PI_GCS2_DLL.dll" (ByVal szHostname As String, ByVal port As Long) As Long
Public Declare Function PI_EnableTCPIPScan Lib "PI_GCS2_DLL.dll" (ByVal iMask As Long) As Long
Public Declare Function PI_EnumerateTCPIPDevices Lib "PI_GCS2_DLL.dll" (ByVal szBuffer As String, ByVal iBufferSize As Long, ByVal szFilter As String) As Long
Public Declare Function PI_ConnectTCPIPByDescription Lib "PI_GCS2_DLL.dll" (ByVal szDescription As String) As Long

Public Declare Function PI_EnumerateUSB Lib "PI_GCS2_DLL.dll" (ByVal szBuffer As String, ByVal iBufferSize As Long, ByVal szFilter As String) As Long
Public Declare Function PI_ConnectUSB Lib "PI_GCS2_DLL.dll" (ByVal szDescription As String) As Long
Public Declare Function PI_ConnectUSBWithBaudRate Lib "PI_GCS2_DLL.dll" (ByVal szDescription As String, ByVal iBaudRate As Long) As Long
Public Declare Function PI_OpenUSBDaisyChain Lib "PI_GCS2_DLL.dll" (ByVal szDescription As String, ByRef pNumberOfConnectedDaisyChainDevices As Long, ByVal szDeviceIDNs As String, ByVal iBufferSize As Long) As Long

Public Declare Function PI_IsConnected Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Sub PI_CloseConnection Lib "PI_GCS2_DLL.dll" (ByVal ID As Long)
Public Declare Function PI_GetError Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_SetErrorCheck Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal bErrorCheck As Long) As Long
Public Declare Function PI_TranslateError Lib "PI_GCS2_DLL.dll" (ByVal errNr As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long




'/////////////////////////////////////////////////////////////////////////////
'// general
Public Declare Function PI_qERR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef pnError As Long) As Long
Public Declare Function PI_qIDN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_INI Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_qHLP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qHPA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qHPV Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qCSV Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef pdCommandSyntaxVersion As Double) As Long
Public Declare Function PI_qOVF Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef piValueArray As Long) As Long
Public Declare Function PI_RBT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_REP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_BDR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iBaudRate As Long) As Long
Public Declare Function PI_qBDR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iBaudRate As Long) As Long
Public Declare Function PI_DBR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iBaudRate As Long) As Long
Public Declare Function PI_qDBR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iBaudRate As Long) As Long
Public Declare Function PI_qVER Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qSSN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szSerialNumber As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_CCT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iCommandType As Long) As Long
Public Declare Function PI_qCCT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iCommandType As Long) As Long
Public Declare Function PI_qTVI Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_IFC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szParameters As String, ByVal szValues As String) As Long
Public Declare Function PI_qIFC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szParameters As String, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_IFS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szPassWord As String, ByVal szParameters As String, ByVal szValues As String) As Long
Public Declare Function PI_qIFS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szParameters As String, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qPUN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByVal szUnit As String, ByVal iBufferSize As Long) As Long

Public Declare Function PI_MOV Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qMOV Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_MVR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_POS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qPOS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_IsMoving Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_HLT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_STP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_qONT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_RTO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_qRTO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef piValueArray As Long) As Long
Public Declare Function PI_ATZ Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdLowvoltageArray As Double, ByRef pfUseDefaultArray As Long) As Long
Public Declare Function PI_qATZ Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef piAtzResultArray As Long) As Long
Public Declare Function PI_AOS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qAOS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArrayas As Double) As Long

Public Declare Function PI_SVA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qSVA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_SVR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long

Public Declare Function PI_DFH Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_qDFH Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_GOH Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long

Public Declare Function PI_qCST Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByVal szNames As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_CST Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByVal szNames As String) As Long
Public Declare Function PI_qVST Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long

Public Declare Function PI_SVO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qSVO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_SMO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef piValueArray As Long) As Long
Public Declare Function PI_qSMO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef piValueArray As Long) As Long
Public Declare Function PI_DCO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qDCO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_BRA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qBRA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long

Public Declare Function PI_RON Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qRON Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long

Public Declare Function PI_VEL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qVEL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long

Public Declare Function PI_qTCV Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long

Public Declare Function PI_ACC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qACC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long

Public Declare Function PI_DEC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qDEC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long

Public Declare Function PI_VCO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qVCO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long

Public Declare Function PI_SPA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iParameterArray As Long, ByRef pdValueArray As Double, ByVal szStrings As String) As Long
Public Declare Function PI_qSPA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iParameterArray As Long, ByRef pdValueArray As Double, ByVal szStrings As String, ByVal iMaxNameSize As Long) As Long
Public Declare Function PI_SEP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szPassWord As String, ByVal szAxes As String, ByRef iParameterArray As Long, ByRef pdValueArray As Double, ByVal szStrings As String) As Long
Public Declare Function PI_qSEP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iParameterArray As Long, ByRef pdValueArray As Double, ByVal szStrings As String, ByVal iMaxNameSize As Long) As Long
Public Declare Function PI_WPA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szPassWord As String, ByVal szAxes As String, ByRef iParameterArray As Long) As Long
Public Declare Function PI_RPA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iParameterArray As Long) As Long
Public Declare Function PI_SPA_String Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iParameterArray As Long, ByVal szStrings As String) As Long
Public Declare Function PI_qSPA_String Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iParameterArray As Long, ByVal szStrings As String, ByVal iMaxNameSize As Long) As Long
Public Declare Function PI_SEP_String Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szPassWord As String, ByVal szAxes As String, ByRef iParameterArray As Long, ByVal szStrings As String) As Long
Public Declare Function PI_qSEP_String Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iParameterArray As Long, ByVal szStrings As String, ByVal iMaxNameSize As Long) As Long

Public Declare Function PI_STE Lib "PI_GCS2_DLL.dll" (ByVal iId As Long, ByVal szAxes As String, ByRef dOffsetArray As Double) As Long
Public Declare Function PI_qSTE Lib "PI_GCS2_DLL.dll" (ByVal iId As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_IMP Lib "PI_GCS2_DLL.dll" (ByVal iId As Long, ByVal szAxes As String, ByVal pdImpulseSize As Double) As Long
Public Declare Function PI_IMP_PulseWidth Lib "PI_GCS2_DLL.dll" (ByVal iId As Long, ByVal cAxis As Byte, ByVal dOffset As Double, ByVal iPulseWidth As Long) As Long
Public Declare Function PI_qIMP Lib "PI_GCS2_DLL.dll" (ByVal iId As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long

Public Declare Function PI_SAI Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szOldAxes As String, ByVal szNewAxes As String) As Long
Public Declare Function PI_qSAI Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qSAI_ALL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByVal iBufferSize As Long) As Long

Public Declare Function PI_CCL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iComandLevel As Long, ByVal szPassWord As String) As Long
Public Declare Function PI_qCCL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piComandLevel As Long) As Long

Public Declare Function PI_AVG Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iAverrageTime As Long) As Long
Public Declare Function PI_qAVG Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iAverrageTime As Long) As Long

Public Declare Function PI_qHAR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qLIM Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qTRS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_FNL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_FPL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_FRF Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_FED Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef piEdgeArray As Long, ByRef piParamArray As Long) As Long
Public Declare Function PI_qFRF Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_DIO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piChannelsArray As Long, ByRef pbValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qDIO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piChannelsArray As Long, ByRef pbValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTIO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piInputNr As Long, ByRef piOutputNr As Long) As Long
Public Declare Function PI_IsControllerReady Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piControllerReady As Long) As Long
Public Declare Function PI_qSRG Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef iRegisterArray As Long, ByRef iValArray As Long) As Long

Public Declare Function PI_ATC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal piChannels As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qATC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal piChannels As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qATS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal piChannels As Long, ByVal piOptions As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long

'/////////////////////////////////////////////////////////////////////////////
'// Macro commande
Public Declare Function PI_IsRunningMacro Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef pbRunningMacro As Long) As Long
Public Declare Function PI_MAC_BEG Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szMacroName As String) As Long
Public Declare Function PI_MAC_START Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szMacroName As String) As Long
Public Declare Function PI_MAC_NSTART Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szMacroName As String, ByVal nrRuns As Long) As Long
Public Declare Function PI_MAC_END Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_MAC_DEL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szMacroName As String) As Long
Public Declare Function PI_MAC_DEF Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szMacroName As String) As Long
Public Declare Function PI_MAC_qDEF Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qMAC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szMacroName As String, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qRMC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long

Public Declare Function PI_DEL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal nMilliSeconds As Long) As Long
Public Declare Function PI_WAC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szCondition As String) As Long
Public Declare Function PI_MEX Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szCondition As String) As Long

'/////////////////////////////////////////////////////////////////////////////
'// String commands.
Public Declare Function PI_GcsCommandset Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szCommand As String) As Long
Public Declare Function PI_GcsGetAnswer Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAnswer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_GcsGetAnswerSize Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iAnswerSize As Long) As Long


'/////////////////////////////////////////////////////////////////////////////
'// limits
Public Declare Function PI_qTMN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qTMX Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_NLM Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qNLM Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_PLM Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qPLM Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pdValueArray As Double) As Long
Public Declare Function PI_SSL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long
Public Declare Function PI_qSSL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String, ByRef pbValueArray As Long) As Long


'/////////////////////////////////////////////////////////////////////////////
'// Wave commands.
Public Declare Function PI_IsGeneratorRunning Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal piWaveGeneratorIds As Long, ByRef pbValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTWG Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGenerators As Long) As Long
Public Declare Function PI_WAV_SIN_P Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iWaveTableId As Long, ByVal iOffsetOfFirstPoIntegerInWaveTable As Long, ByVal iNumberOfPoIntegers As Long, ByVal iAddAppendWave As Long, ByVal iCenterPoIntegerOfWave As Long, ByVal dAmplitudeOfWave As Double, ByVal dOffsetOfWave As Double, ByVal iSegmentLength As Long) As Long
Public Declare Function PI_WAV_LIN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iWaveTableId As Long, ByVal iOffsetOfFirstPoIntegerInWaveTable As Long, ByVal iNumberOfPoIntegers As Long, ByVal iAddAppendWave As Long, ByVal iNumberOfSpeedUpDownPoIntegersInWave As Long, ByVal dAmplitudeOfWave As Double, ByVal dOffsetOfWave As Double, ByVal iSegmentLength As Long) As Long
Public Declare Function PI_WAV_RAMP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iWaveTableId As Long, ByVal iOffsetOfFirstPoIntegerInWaveTable As Long, ByVal iNumberOfPoIntegers As Long, ByVal iAddAppendWave As Long, ByVal iCenterPoIntegerOfWave As Long, ByVal iNumberOfSpeedUpDownPoIntegersInWave As Long, ByVal dAmplitudeOfWave As Double, ByVal dOffsetOfWave As Double, ByVal iSegmentLength As Long) As Long
Public Declare Function PI_WAV_PNT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iWaveTableId As Long, ByVal iOffsetOfFirstPoIntegerInWaveTable As Long, ByVal iNumberOfPoIntegers As Long, ByVal iAddAppendWave As Long, ByVal pdWavePoIntegers As Double) As Long
Public Declare Function PI_qWAV Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveTableIdsArray As Long, ByRef piParamereIdsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_WGO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef iStartModArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qWGO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_WGC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef piNumberOfCyclesArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qWGC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_WSL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef piWaveTableIdsArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qWSL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef piWaveTableIdsArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_DTC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piDdlTableIdsArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_WCL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveTableIdsArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTLT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piNumberOfDdlTables As Long) As Long
Public Declare Function PI_qGWD_SYNC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iWaveTableId As Long, ByVal iOffsetOfFirstPoIntegerInWaveTable As Long, ByVal iNumberOfValues As Long, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qGWD Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iWaveTableIdsArray As Long, ByVal iNumberOfWaveTables As Long, ByVal iOffset As Long, ByVal nrValues As Long, ByRef pdValarray As Long, ByVal szGcsArrayHeader As String, ByVal iGcsArrayHeaderMaxSize As Long) As Long
Public Declare Function PI_WOS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iWaveTableIdsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qWOS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iWaveTableIdsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_WTR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef piTableRateArray As Long, ByRef piIntegererpolationTypeArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qWTR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveGeneratorIdsArray As Long, ByRef piTableRateArray As Long, ByRef piIntegererpolationTypeArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_DDL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iDdlTableId As Long, ByVal iOffsetOfFirstPointInDdlTable As Long, ByVal iNumberOfValues As Long, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qDDL_SYNC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iDdlTableId As Long, ByVal iOffsetOfFirstPoIntegerInDdlTable As Long, ByVal iNumberOfValues As Long, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qDDL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iDdlTableIdsArray As Long, ByVal iNumberOfDdlTables As Long, ByVal iOffsetOfFirstPoIntegerInDdlTable As Long, ByVal iNumberOfValues As Long, ByRef pdValueArray As Long, ByVal szGcsArrayHeader As String, ByVal iGcsArrayHeaderMaxSize As Long) As Long
Public Declare Function PI_DPO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_qWMS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piWaveTableIdsArray As Long, ByRef iWaveTableMaimumSize As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qDTL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piDdlTableIdsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_TWE Lib "PI_GCS2_DLL.dll" (ByVal ID As Long,  ByRef  piWaveTableIdsArray As Long, ByRef piWaveTableStartIndexArray As Long, ByRef piWaveTableEndIndexArray As Long, ByVal iArraySize As Long);
Public Declare Function PI_qTWE Lib "PI_GCS2_DLL.dll" (ByVal ID As Long,  ByRef  piWaveTableIdsArray As Long, ByRef piWaveTableStartIndexArray As Long, ByRef piWaveTableEndIndexArray As Long, ByVal iArraySize As Long);



'///////////////////////////////////////////////////////////////////////////////
'//// Trigger commands.
Public Declare Function PI_TWC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_TWS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piTriggerChannelIdsArray As Long, ByRef piPointNumberArray As Long, ByRef piSwitchArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTWS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iTriggerChannelIdsArray As Long, ByVal iNumberOfTriggerChannels As Long, ByVal iOffset As Long, ByVal nrValues As Long, ByRef pdValarray As Long, ByVal szGcsArrayHeader As String, ByVal iGcsArrayHeaderMaxSize As Long) As Long
Public Declare Function PI_CTO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piTriggerOutputIdsArray As Long, ByRef piTriggerParameterArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qCTO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piTriggerOutputIdsArray As Long, ByRef piTriggerParameterArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_TRO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piTriggerChannelIds As Long, ByRef pbTriggerChannelEnabel As Long, byvaliArraySizeas As Long) As Long
Public Declare Function PI_qTRO Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piTriggerChannelIds As Long, ByRef pbTriggerChannelEnabel As Long, ByVal iArraySize As Long) As Long


'/////////////////////////////////////////////////////////////////////////////
'// Record tabel commands.
Public Declare Function PI_qHDR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qTNR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piNumberOfRecordCannels As Long) As Long
Public Declare Function PI_DRC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piRecordTableIdsArray As Long, ByVal szRecordSourceIds As String, ByRef piRecordOptionArray As Long) As Long
Public Declare Function PI_qDRC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piRecordTableIdsArray As Long, ByVal szRecordSourceIds As String, ByRef piRecordOptionArray As Long, ByVal iRecordSourceIdsBufferSize As Long, ByVal iRecordOptionArraySize As Long) As Long
Public Declare Function PI_qDRR_SYNC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iRecordTablelId As Long, ByVal iOffsetOfFirstPoIntegerInRecordTable As Long, ByVal iNumberOfValues As Long, ByRef pdValueArray As Double) As Long
Public Declare Function PI_qDRR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piRecTableIdsArray As Long, ByVal iNumberOfRecChannels As Long, ByVal iOffsetOfFirstPoIntegerInRecordTable As Long, ByVal iNumberOfValues As Long, ByRef pdValueArray As Long, ByVal szGcsArrayHeader As String, ByVal iGcsArrayHeaderMaxSize As Long) As Long
Public Declare Function PI_DRT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piRecordChannelIdsArray As Long, ByRef piTriggerSourceArray As Long, ByVal szValues As String, ByVal iArraySize As Long) As Long
Public Declare Function PI_qDRT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piRecordChannelIdsArray As Long, ByRef piTriggerSourceArray As Long, ByVal szValues As String, ByVal iArraySize As Long, ByVal iValueBufferLength As Long) As Long
Public Declare Function PI_RTR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal piReportTableRate As Long) As Long
Public Declare Function PI_qRTR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piReportTableRate As Long) As Long
Public Declare Function PI_WGR Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long


'/////////////////////////////////////////////////////////////////////////////
'// Piezo-Channel commands.
Public Declare Function PI_VMA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qVMA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_VMI Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qVMI Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_VOL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qVOL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTPC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piNumberOfPiezoChannels As Long) As Long
Public Declare Function PI_ONL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoCannelsArray As Long, ByRef pdValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qONL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPiezoCannelsArray As Long, ByRef pdValueArray As Long, ByVal iArraySize As Long) As Long


'/////////////////////////////////////////////////////////////////////////////
'// Sensor-Channel commands.
Public Declare Function PI_qTAD Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piSensorsChannelsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTNS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piSensorsChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTSP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piSensorsChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_SCN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piSensorsChannelsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qSCN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piSensorsChannelsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTSC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piNumberOfSensorChannels As Long) As Long


'/////////////////////////////////////////////////////////////////////////////
'// PIEZOWALK(R)-Channel commands.
Public Declare Function PI_APG Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef iArraySize As Long) As Long
Public Declare Function PI_qAPG Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_OAD Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qOAD Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_OCD Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qOCD Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_OSM Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qOSM Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_OVL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qOVL Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qOSN Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_SSA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qSSA Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_RNP Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_PGS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piPIEZOWALKChannelsArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qTAC Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef pnNrChannels As Long) As Long
Public Declare Function PI_qTAV Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piChannelsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long

'/////////////////////////////////////////////////////////////////////////////
'// Joystick
Public Declare Function PI_qJAS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iJoystickIDsArray As Long, ByRef iAxesIDsArray As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_JAX Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iJoystickID As Long, ByVal iAxesID As Long, ByVal szAxesBuffer As String) As Long
Public Declare Function PI_qJAX Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iJoystickIDsArray As Long, ByRef iAxesIDsArray As Long, ByVal iArraySize As Long, ByVal szAxesBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_qJBS Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iJoystickIDsArray As Long, ByRef iButtonIDsArray As Long, ByRef pbValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_JDT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iJoystickIDsArray As Long, ByRef iAxisIDsArray As Long, ByRef piValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_JLT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal iJoystickID As Long, ByVal iAxisID As Long, ByVal iStartAdress As Long, ByRef pdValueArray As Double, ByVal iArraySize As Long) As Long
Public Declare Function PI_qJLT Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iJoystickIDsArray As Long, ByRef iAxisIDsArray As Long, ByVal iNumberOfTables As Long, ByVal iOffsetOfFirstPoIntegerIntegerable As Long, ByVal iNumberOfValues As Long, ByRef pdValueArray As Long, ByVal szGcsArrayHeader As String, ByVal iGcsArrayHeaderMaxSize As Long) As Long
Public Declare Function PI_JON Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iJoystickIDsArray As Long, ByRef pbValueArray As Long, ByVal iArraySize As Long) As Long
Public Declare Function PI_qJON Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef iJoystickIDsArray As Long, ByRef pbValueArray As Long, ByVal iArraySize As Long) As Long




'/////////////////////////////////////////////////////////////////////////////
'// Spezial
Public Declare Function PI_GetSupportedFunctions Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piComandLevelArray As Long, ByVal iiBufferSize As Long, ByVal szFunctionNames As String, ByVal iMaxFunctioNamesLength As Long) As Long
Public Declare Function PI_GetSupportedParameters Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef piParameterIdArray As Long, ByRef piComandLevelArray As Long, ByRef piMennoryLocationArray As Long, ByRef piDataTypeArray As Long, ByRef piNumberOfItems As Long, ByVal iiBufferSize As Long, ByVal szParameterName As String, ByVal iMaxParameterNameSize As Long) As Long
Public Declare Function PI_GetSupportedControllers Lib "PI_GCS2_DLL.dll" (ByVal szBuffer As String, ByVal iBufferSize As Long) As Long
Public Declare Function PI_GetAsyncBufferIndex Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_GetAsyncBuffer Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByRef pdValueArray() As Double) As Long


Public Declare Function PI_AddStage Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szAxes As String) As Long
Public Declare Function PI_RemoveStage Lib "PI_GCS2_DLL.dll" (ByVal ID As Long, ByVal szStageName As String) As Long
Public Declare Function PI_OpenUserStagesEditDialog Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long
Public Declare Function PI_OpenPiStagesEditDialog Lib "PI_GCS2_DLL.dll" (ByVal ID As Long) As Long

