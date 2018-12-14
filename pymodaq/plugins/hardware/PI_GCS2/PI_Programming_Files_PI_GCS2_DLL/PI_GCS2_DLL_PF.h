/////////////////////////////////////////////////////////////////////////////
// This is a part of the PI-Software Sources
// (c)2008-2015 Physik Instrumente (PI) GmbH & Co. KG
// All rights reserved.
//

///////////////////////////////////////////////////////////////////////////// 
// Program: PI_G-Control DLL
//
// Developer: JKa
//  
// File: PI_GCS_DLL.h : 
/////////////////////////////////////////////////////////////////////////////


#ifdef __cplusplus
extern "C" {
#endif

#ifdef WIN32
	#undef PI_FUNC_DECL
	#define PI_FUNC_DECL WINAPI
#else
	#define PI_FUNC_DECL
#endif


#ifndef WIN32
	#ifndef BOOL
	#define BOOL int
	#endif

	#ifndef TRUE
	#define TRUE 1
	#endif

	#ifndef FALSE
	#define FALSE 0
	#endif

	#ifndef __int64
		#define	__int64	int64_t
	#endif


#endif //WIN32



////////////////////////////////
// E-7XX Bits (PI_BIT_XXX). //
////////////////////////////////

/* Curve Controll PI_BIT_WGO_XXX */
#define PI_BIT_WGO_START_DEFAULT			0x00000001U
#define PI_BIT_WGO_START_EXTERN_TRIGGER		0x00000002U
#define PI_BIT_WGO_WITH_DDL_INITIALISATION	0x00000040U
#define PI_BIT_WGO_WITH_DDL					0x00000080U
#define PI_BIT_WGO_START_AT_ENDPOSITION		0x00000100U
#define PI_BIT_WGO_SINGLE_RUN_DDL_TEST		0x00000200U
#define PI_BIT_WGO_EXTERN_WAVE_GENERATOR	0x00000400U
#define PI_BIT_WGO_SAVE_BIT_1				0x00100000U
#define PI_BIT_WGO_SAVE_BIT_2				0x00200000U
#define PI_BIT_WGO_SAVE_BIT_3				0x00400000U

/* Wave-Trigger PI_BIT_TRG_XXX */
#define	PI_BIT_TRG_LINE_1					0x0001U
#define	PI_BIT_TRG_LINE_2					0x0002U
#define	PI_BIT_TRG_LINE_3					0x0003U
#define	PI_BIT_TRG_LINE_4					0x0008U
#define	PI_BIT_TRG_ALL_CURVE_POINTS			0x0100U

/* Data Record Configuration PI_DRC_XXX */
#define	PI_DRC_DEFAULT					0U
#define	PI_DRC_AXIS_TARGET_POS			1U
#define	PI_DRC_AXIS_ACTUAL_POS			2U
#define	PI_DRC_AXIS_POS_ERROR			3U
#define	PI_DRC_AXIS_DDL_DATA			4U
#define	PI_DRC_AXIS_DRIVING_VOL			5U
#define	PI_DRC_PIEZO_MODEL_VOL			6U
#define	PI_DRC_PIEZO_VOL				7U
#define	PI_DRC_SENSOR_POS				8U


/* P(arameter)I(nfo)F(lag)_M(emory)T(ype)_XX */
#define PI_PIF_MT_RAM					0x00000001U
#define PI_PIF_MT_EPROM					0x00000002U
#define PI_PIF_MT_ALL					(PI_PIF_MT_RAM | PI_PIF_MT_EPROM)

/* P(arameter)I(nfo)F(lag)_D(ata)T(ype)_XX */
#define PI_PIF_DT_INT					1U
#define PI_PIF_DT_FLOAT					2U
#define PI_PIF_DT_CHAR					3U


/////////////////////////////////////////////////////////////////////////////
// DLL initialization and comm functions
typedef int (PI_FUNC_DECL * PFPI_InterfaceSetupDlg)(const char* szRegKeyName);
typedef int (PI_FUNC_DECL * PFPI_ConnectRS232)(int nPortNr, int iBaudRate);
#ifndef WIN32
typedef int (PI_FUNC_DECL * PFPI_ConnectRS232ByDevName)(const char* szDevName, int BaudRate);
#endif
typedef int (PI_FUNC_DECL * PFPI_OpenRS232DaisyChain)(int iPortNumber, int iBaudRate, int* pNumberOfConnectedDaisyChainDevices, char* szDeviceIDNs, int iBufferSize);
typedef int (PI_FUNC_DECL * PFPI_ConnectDaisyChainDevice)(int iPortId, int iDeviceNumber);
typedef void (PI_FUNC_DECL * PFPI_CloseDaisyChain)(int iPortId);

typedef int (PI_FUNC_DECL * PFPI_ConnectNIgpib)(int nBoard, int nDevAddr);

typedef int (PI_FUNC_DECL * PFPI_ConnectTCPIP)(const char* szHostname, int port);
typedef int (PI_FUNC_DECL * PFPI_EnableTCPIPScan)(int iMask);
typedef int (PI_FUNC_DECL * PFPI_EnumerateTCPIPDevices)(char* szBuffer, int iBufferSize, const char* szFilter);
typedef int (PI_FUNC_DECL * PFPI_ConnectTCPIPByDescription)(const char* szDescription);
typedef int (PI_FUNC_DECL * PFPI_OpenTCPIPDaisyChain)(const char* szHostname, int port, int* pNumberOfConnectedDaisyChainDevices, char* szDeviceIDNs, int iBufferSize);

typedef int (PI_FUNC_DECL * PFPI_EnumerateUSB)(char* szBuffer, int iBufferSize, const char* szFilter);
typedef int (PI_FUNC_DECL * PFPI_ConnectUSB)(const char* szDescription);
typedef int (PI_FUNC_DECL * PFPI_ConnectUSBWithBaudRate)(const char* szDescription,int iBaudRate);
typedef int (PI_FUNC_DECL * PFPI_OpenUSBDaisyChain)(const char* szDescription, int* pNumberOfConnectedDaisyChainDevices, char* szDeviceIDNs, int iBufferSize);

typedef BOOL (PI_FUNC_DECL * PFPI_IsConnected)(int ID);
typedef void (PI_FUNC_DECL * PFPI_CloseConnection)(int ID);
typedef int (PI_FUNC_DECL * PFPI_GetError)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_SetErrorCheck)(int ID, BOOL bErrorCheck);
typedef BOOL (PI_FUNC_DECL * PFPI_TranslateError)(int errNr, char* szBuffer, int iBufferSize);
typedef int (PI_FUNC_DECL * PFPI_SetTimeout)(int ID, int timeoutInMS);

typedef int (PI_FUNC_DECL * PFPI_SetDaisyChainScanMaxDeviceID)(int maxID);

typedef BOOL (PI_FUNC_DECL * PFPI_EnableReconnect)(int ID, BOOL bEnable);
typedef int (PI_FUNC_DECL * PFPI_SetNrTimeoutsBeforeClose)(int ID, int nrTimeoutsBeforeClose);


/////////////////////////////////////////////////////////////////////////////
// general
typedef BOOL (PI_FUNC_DECL * PFPI_qERR)(int ID, int* pnError);
typedef BOOL (PI_FUNC_DECL * PFPI_qIDN)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_INI)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_qHLP)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHPA)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHPV)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qCSV)(int ID, double* pdCommandSyntaxVersion);
typedef BOOL (PI_FUNC_DECL * PFPI_qOVF)(int ID, const char* szAxes, BOOL* piValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_RBT)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_REP)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_BDR)(int ID, int iBaudRate);
typedef BOOL (PI_FUNC_DECL * PFPI_qBDR)(int ID, int* iBaudRate);
typedef BOOL (PI_FUNC_DECL * PFPI_DBR)(int ID, int iBaudRate);
typedef BOOL (PI_FUNC_DECL * PFPI_qDBR)(int ID, int* iBaudRate);
typedef BOOL (PI_FUNC_DECL * PFPI_qVER)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qSSN)(int ID, char* szSerialNumber, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_CCT)(int ID, int iCommandType);
typedef BOOL (PI_FUNC_DECL * PFPI_qCCT)(int ID, int *iCommandType);
typedef BOOL (PI_FUNC_DECL * PFPI_qTVI)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_IFC)(int ID, const char* szParameters, const char* szValues);
typedef BOOL (PI_FUNC_DECL * PFPI_qIFC)(int ID, const char* szParameters, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_IFS)(int ID, const char* szPassword, const char* szParameters, const char* szValues);
typedef BOOL (PI_FUNC_DECL * PFPI_qIFS)(int ID, const char* szParameters, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qECO)(int ID, const char* szSendString, char* szValues, int iBufferSize);

typedef BOOL (PI_FUNC_DECL * PFPI_MOV)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qMOV)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_MVR)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_MVE)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_POS)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qPOS)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_IsMoving)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_HLT)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_STP)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_StopAll)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_qONT)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_RTO)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_qRTO)(int ID, const char* szAxes, int* piValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_ATZ)(int ID, const char* szAxes, const double* pdLowvoltageArray, const BOOL* pfUseDefaultArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qATZ)(int ID, const char* szAxes, int* piAtzResultArray);
typedef BOOL (PI_FUNC_DECL * PFPI_AOS)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qAOS)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_HasPosChanged)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_GetErrorStatus)(int ID, BOOL* pbIsReferencedArray, BOOL* pbIsReferencing, BOOL* pbIsMovingArray, BOOL* pbIsMotionErrorArray);


typedef BOOL (PI_FUNC_DECL * PFPI_SVA)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSVA)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_SVR)(int ID, const char* szAxes, const double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_DFH)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_qDFH)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_GOH)(int ID, const char* szAxes);

typedef BOOL (PI_FUNC_DECL * PFPI_qCST)(int ID, const char* szAxes, char* szNames, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_CST)(int ID, const char* szAxes, const char* szNames);
typedef BOOL (PI_FUNC_DECL * PFPI_qVST)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qPUN)(int ID, const char* szAxes, char* szUnit, int iBufferSize);

typedef BOOL (PI_FUNC_DECL * PFPI_SVO)(int ID, const char* szAxes, const BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSVO)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_SMO)( int ID, const char*  szAxes, const int* piValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSMO)(int ID, const char* szAxes, int* piValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_DCO)(int ID, const char* szAxes, const BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qDCO)(int ID, const char* szAxes, BOOL* pbValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_BRA)(int ID, const char* szAxes, const BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qBRA)(int ID, const char* szAxes, BOOL* pbValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_RON)(int ID, const char* szAxes, const BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qRON)(int ID, const char* szAxes, BOOL* pbValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_VEL)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qVEL)(int ID, const char* szAxes, double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_JOG)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qJOG)(int ID, const char* szAxes, double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_qTCV)(int ID, const char* szAxes, double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_VLS)(int ID, double dSystemVelocity);
typedef BOOL (PI_FUNC_DECL * PFPI_qVLS)(int ID, double* pdSystemVelocity);

typedef BOOL (PI_FUNC_DECL * PFPI_ACC)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qACC)(int ID, const char* szAxes, double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_DEC)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qDEC)(int ID, const char* szAxes, double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_VCO)(int ID, const char* szAxes, const BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qVCO)(int ID, const char* szAxes, BOOL* pbValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_SPA)(int ID, const char* szAxes, const unsigned int* iParameterArray, const double* pdValueArray, const char* szStrings);
typedef BOOL (PI_FUNC_DECL * PFPI_qSPA)(int ID, const char* szAxes, unsigned int* iParameterArray, double* pdValueArray, char* szStrings, int iMaxNameSize);
typedef BOOL (PI_FUNC_DECL * PFPI_SEP)(int ID, const char* szPassword, const char* szAxes, const unsigned int* iParameterArray, const double* pdValueArray, const char* szStrings);
typedef BOOL (PI_FUNC_DECL * PFPI_qSEP)(int ID, const char* szAxes, unsigned int* iParameterArray, double* pdValueArray, char* szStrings, int iMaxNameSize);
typedef BOOL (PI_FUNC_DECL * PFPI_WPA)(int ID, const char* szPassword, const char* szAxes, const unsigned int* iParameterArray);
typedef BOOL (PI_FUNC_DECL * PFPI_DPA)(int ID, const char* szPassword, const char* szAxes, const unsigned int* iParameterArray);
typedef BOOL (PI_FUNC_DECL * PFPI_TIM)(int ID, double dTimer);
typedef BOOL (PI_FUNC_DECL * PFPI_qTIM)(int ID, double* pdTimer);
typedef BOOL (PI_FUNC_DECL * PFPI_RPA)(int ID, const char* szAxes, const unsigned int* iParameterArray);
typedef BOOL (PI_FUNC_DECL * PFPI_SPA_String)(int ID, const char* szAxes, const unsigned int* iParameterArray, const char* szStrings);
typedef BOOL (PI_FUNC_DECL * PFPI_qSPA_String)(int ID, const char* szAxes, const unsigned int* iParameterArray, char* szStrings, int iMaxNameSize);
typedef BOOL (PI_FUNC_DECL * PFPI_SEP_String)(int ID, const char* szPassword, const char* szAxes, const unsigned int* iParameterArray, const char* szStrings);
typedef BOOL (PI_FUNC_DECL * PFPI_qSEP_String)(int ID, const char* szAxes, unsigned int* iParameterArray, char* szStrings, int iMaxNameSize);
typedef BOOL (PI_FUNC_DECL * PFPI_SPA_int64)(int ID, const char* szAxes, const unsigned int* iParameterArray, const __int64* piValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSPA_int64)(int ID, const char* szAxes, unsigned int* iParameterArray, __int64* piValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_SEP_int64)(int ID, const char* szPassword, const char* szAxes, const unsigned int* iParameterArray, const __int64* piValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSEP_int64)(int ID, const char* szAxes, unsigned int* iParameterArray, __int64* piValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_STE)(int ID, const char* szAxes, const double* dOffsetArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSTE)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_IMP)(int ID, const char*  szAxes, const double* pdImpulseSize);
typedef BOOL (PI_FUNC_DECL * PFPI_IMP_PulseWidth)(int ID, char cAxis, double dOffset, int iPulseWidth);
typedef BOOL (PI_FUNC_DECL * PFPI_qIMP)(int ID, const char* szAxes, double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_SAI)(int ID, const char* szOldAxes, const char* szNewAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_qSAI)(int ID, char* szAxes, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qSAI_ALL)(int ID, char* szAxes, int iBufferSize);

typedef BOOL (PI_FUNC_DECL * PFPI_CCL)(int ID, int iComandLevel, const char* szPassWord);
typedef BOOL (PI_FUNC_DECL * PFPI_qCCL)(int ID, int* piComandLevel);

typedef BOOL (PI_FUNC_DECL * PFPI_AVG)(int ID, int iAverrageTime);
typedef BOOL (PI_FUNC_DECL * PFPI_qAVG)(int ID, int *iAverrageTime);

typedef BOOL (PI_FUNC_DECL * PFPI_qHAR)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qLIM)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qTRS)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_FNL)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_FPL)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_FRF)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_FED)(int ID, const char* szAxes, const int* piEdgeArray, const int* piParamArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qFRF)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_DIO)(int ID, const int* piChannelsArray, const BOOL* pbValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qDIO)(int ID, const int* piChannelsArray, BOOL* pbValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTIO)(int ID, int* piInputNr, int* piOutputNr);
typedef BOOL (PI_FUNC_DECL * PFPI_IsControllerReady)(int ID, int* piControllerReady);
typedef BOOL (PI_FUNC_DECL * PFPI_qSRG)(int ID, const char* szAxes, const int* iRegisterArray, int* iValArray);

typedef BOOL (PI_FUNC_DECL * PFPI_ATC)(int ID, const int* piChannels, const int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qATC)(int ID, const int* piChannels, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qATS)(int ID, const int* piChannels, const int* piOptions, int* piValueArray, int iArraySize);

typedef BOOL (PI_FUNC_DECL * PFPI_SPI)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSPI)(int ID, const char* szAxes, double* pdValueArray);

typedef BOOL (PI_FUNC_DECL * PFPI_SCT)(int ID, double dCycleTime);
typedef BOOL (PI_FUNC_DECL * PFPI_qSCT)(int ID, double* pdCycleTime);

typedef BOOL (PI_FUNC_DECL * PFPI_SST)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSST)(int ID, const char* szAxes, double* pdValueArray);

/////////////////////////////////////////////////////////////////////////////
// Macro commande
typedef BOOL (PI_FUNC_DECL * PFPI_IsRunningMacro)(int ID, BOOL* pbRunningMacro);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_BEG)(int ID, const char* szMacroName);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_START)(int ID, const char* szMacroName);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_NSTART)(int ID, const char* szMacroName, int nrRuns);

typedef BOOL (PI_FUNC_DECL * PFPI_MAC_START_Args)(int ID, const char* szMacroName, const char* szArgs);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_NSTART_Args)(int ID, const char* szMacroName, int nrRuns, const char* szArgs);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_END)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_DEL)(int ID, const char* szMacroName);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_DEF)(int ID, const char* szMacroName);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_qDEF)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_qERR)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_MAC_qFREE)(int ID, int* iFreeSpace);
typedef BOOL (PI_FUNC_DECL * PFPI_qMAC)(int ID, const char* szMacroName, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qRMC)(int ID, char* szBuffer, int iBufferSize);

typedef BOOL (PI_FUNC_DECL * PFPI_DEL)(int ID, int nMilliSeconds);
typedef BOOL (PI_FUNC_DECL * PFPI_WAC)(int ID, const char* szCondition);
typedef BOOL (PI_FUNC_DECL * PFPI_MEX)(int ID, const char* szCondition);

typedef BOOL (PI_FUNC_DECL * PFPI_VAR)(int ID, const char* szVariables, const char* szValues);
typedef BOOL (PI_FUNC_DECL * PFPI_qVAR)(int ID, const char* szVariables, char* szValues,  int iBufferSize);

/////////////////////////////////////////////////////////////////////////////
// String commands.
typedef BOOL (PI_FUNC_DECL * PFPI_GcsCommandset)(int ID, const char* szCommand);
typedef BOOL (PI_FUNC_DECL * PFPI_GcsGetAnswer)(int ID, char* szAnswer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_GcsGetAnswerSize)(int ID, int* iAnswerSize);


/////////////////////////////////////////////////////////////////////////////
// limits
typedef BOOL (PI_FUNC_DECL * PFPI_qTMN)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qTMX)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_NLM)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qNLM)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_PLM)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qPLM)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_SSL)(int ID, const char* szAxes, const BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qSSL)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qVMO)(int ID, const char* szAxes, const double* pdValarray, BOOL* pbMovePossible);


/////////////////////////////////////////////////////////////////////////////
// Wave commands.
typedef BOOL (PI_FUNC_DECL * PFPI_IsGeneratorRunning)(int ID, const int* piWaveGeneratorIds, BOOL* pbValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTWG)(int ID, int* piWaveGenerators);
typedef BOOL (PI_FUNC_DECL * PFPI_WAV_SIN_P)(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iCenterPointOfWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
typedef BOOL (PI_FUNC_DECL * PFPI_WAV_LIN)(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iNumberOfSpeedUpDownPointsInWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
typedef BOOL (PI_FUNC_DECL * PFPI_WAV_RAMP)(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iCenterPointOfWave, int iNumberOfSpeedUpDownPointsInWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
typedef BOOL (PI_FUNC_DECL * PFPI_WAV_PNT)(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, const double* pdWavePoints);
typedef BOOL (PI_FUNC_DECL * PFPI_qWAV)(int ID, const int* piWaveTableIdsArray, const int* piParamereIdsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_WGO)(int ID, const int* piWaveGeneratorIdsArray, const int* iStartModArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qWGO)(int ID, const int* piWaveGeneratorIdsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_WGC)(int ID, const int* piWaveGeneratorIdsArray, const int* piNumberOfCyclesArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qWGC)(int ID, const int* piWaveGeneratorIdsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_WSL)(int ID, const int* piWaveGeneratorIdsArray, const int* piWaveTableIdsArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qWSL)(int ID, const int* piWaveGeneratorIdsArray, int* piWaveTableIdsArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_DTC)(int ID, const int* piDdlTableIdsArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qDTL)(int ID, const int* piDdlTableIdsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_WCL)(int ID, const int* piWaveTableIdsArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTLT)(int ID, int* piNumberOfDdlTables);
typedef BOOL (PI_FUNC_DECL * PFPI_qGWD_SYNC)(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfValues, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qGWD)(int ID, const int* iWaveTableIdsArray, int iNumberOfWaveTables, int iOffset, int nrValues, double** pdValarray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
typedef BOOL (PI_FUNC_DECL * PFPI_WOS)(int ID, const int* iWaveTableIdsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qWOS)(int ID, const int* iWaveTableIdsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_WTR)(int ID, const int* piWaveGeneratorIdsArray, const int* piTableRateArray, const int* piInterpolationTypeArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qWTR)(int ID, const int* piWaveGeneratorIdsArray, int* piTableRateArray, int* piInterpolationTypeArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_DDL)(int ID, int iDdlTableId,  int iOffsetOfFirstPointInDdlTable,  int iNumberOfValues, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qDDL_SYNC)(int ID,  int iDdlTableId,  int iOffsetOfFirstPointInDdlTable,  int iNumberOfValues, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qDDL)(int ID, const int* iDdlTableIdsArray, int iNumberOfDdlTables, int iOffset, int nrValues, double** pdValarray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
typedef BOOL (PI_FUNC_DECL * PFPI_DPO)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_qWMS)(int ID, const int* piWaveTableIds, int* iWaveTableMaximumSize, int iArraySize);



///////////////////////////////////////////////////////////////////////////////
//// Trigger commands.
typedef BOOL (PI_FUNC_DECL * PFPI_TWC)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_TWS)(int ID, const int* piTriggerChannelIdsArray, const int* piPointNumberArray, const int* piSwitchArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTWS)(int ID, const int* iTriggerChannelIdsArray, int iNumberOfTriggerChannels, int iOffset, int nrValues, double** pdValarray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
typedef BOOL (PI_FUNC_DECL * PFPI_CTO)(int ID, const int* piTriggerOutputIdsArray, const int* piTriggerParameterArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_CTOString)(int ID, const int* piTriggerOutputIdsArray, const int* piTriggerParameterArray, const char* szValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qCTO)(int ID, const int* piTriggerOutputIdsArray, const int* piTriggerParameterArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qCTOString)(int ID, const int* piTriggerOutputIdsArray, const int* piTriggerParameterArray, char* szValueArray, int iArraySize, int maxBufLen);
typedef BOOL (PI_FUNC_DECL * PFPI_TRO)(int ID, const int* piTriggerChannelIds, const BOOL* pbTriggerChannelEnabel, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTRO)(int ID, const int* piTriggerChannelIds, BOOL* pbTriggerChannelEnabel, int iArraySize);


/////////////////////////////////////////////////////////////////////////////
// Record tabel commands.
typedef BOOL (PI_FUNC_DECL * PFPI_qHDR)(int ID, char* szBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTNR)(int ID, int* piNumberOfRecordCannels);
typedef BOOL (PI_FUNC_DECL * PFPI_DRC)(int ID, const int* piRecordTableIdsArray, const char* szRecordSourceIds, const int* piRecordOptionArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qDRC)(int ID, const int* piRecordTableIdsArray, char* szRecordSourceIds, int* piRecordOptionArray, int iRecordSourceIdsBufferSize, int iRecordOptionArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qDRR_SYNC)(int ID,  int iRecordTablelId,  int iOffsetOfFirstPointInRecordTable,  int iNumberOfValues, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qDRR)(int ID, const int* piRecTableIdIdsArray,  int iNumberOfRecChannels,  int iOffsetOfFirstPointInRecordTable,  int iNumberOfValues, double** pdValueArray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
typedef BOOL (PI_FUNC_DECL * PFPI_DRT)(int ID, const int* piRecordChannelIdsArray, const int* piTriggerSourceArray, const char* szValues, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qDRT)(int ID, const int* piRecordChannelIdsArray, int* piTriggerSourceArray, char* szValues, int iArraySize, int iValueBufferLength);
typedef BOOL (PI_FUNC_DECL * PFPI_RTR)(int ID, int piReportTableRate);
typedef BOOL (PI_FUNC_DECL * PFPI_qRTR)(int ID, int* piReportTableRate);
typedef BOOL (PI_FUNC_DECL * PFPI_WGR)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_qDRL)(int ID, const int* piRecordChannelIdsArray, int* piNuberOfRecordedValuesArray, int iArraySize);


/////////////////////////////////////////////////////////////////////////////
// Piezo-Channel commands.
typedef BOOL (PI_FUNC_DECL * PFPI_VMA)(int ID, const int* piPiezoChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qVMA)(int ID, const int* piPiezoChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_VMI)(int ID, const int* piPiezoChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qVMI)(int ID, const int* piPiezoChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_VOL)(int ID, const int* piPiezoChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qVOL)(int ID, const int* piPiezoChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTPC)(int ID, int* piNumberOfPiezoChannels);
typedef BOOL (PI_FUNC_DECL * PFPI_ONL)(int ID, const int* iPiezoCannels, const int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qONL)(int ID, const int* iPiezoCannels, int* piValueArray, int iArraySize);


/////////////////////////////////////////////////////////////////////////////
// Sensor-Channel commands.
typedef BOOL (PI_FUNC_DECL * PFPI_qTAD)(int ID, const int* piSensorsChannelsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTNS)(int ID, const int* piSensorsChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTSP)(int ID, const int* piSensorsChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_SCN)(int ID, const int* piSensorsChannelsArray, const int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qSCN)(int ID, const int* piSensorsChannelsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTSC)(int ID, int* piNumberOfSensorChannels);


/////////////////////////////////////////////////////////////////////////////
// PIEZOWALK(R)-Channel commands.
typedef BOOL (PI_FUNC_DECL * PFPI_APG)(int ID, const int* piPIEZOWALKChannelsArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qAPG)(int ID, const int* piPIEZOWALKChannelsArray, int* piValueArray, int iArraySize);

typedef BOOL (PI_FUNC_DECL * PFPI_OAC)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qOAC)(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_OAD)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qOAD)(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_ODC)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qODC)(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_OCD)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qOCD)(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_OSM)(int ID, const int* piPIEZOWALKChannelsArray, const int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qOSM)(int ID, const int* piPIEZOWALKChannelsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_OSMf)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qOSMf)(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_OVL)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qOVL)(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qOSN)(int ID, const int* piPIEZOWALKChannelsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_SSA)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qSSA)(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_RNP)(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_PGS)(int ID, const int* piPIEZOWALKChannelsArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qTAC)(int ID, int* pnNrChannels);
typedef BOOL (PI_FUNC_DECL * PFPI_qTAV)(int ID, const int* piChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_OMA)(int ID, const char* szAxes, const double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qOMA)(int ID, const char* szAxes, double* pdValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_OMR)(int ID, const char* szAxes, const double* pdValueArray);

/////////////////////////////////////////////////////////////////////////////
// Joystick
typedef BOOL (PI_FUNC_DECL * PFPI_qJAS)(int ID, const int* iJoystickIDsArray, const int* iAxesIDsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_JAX)(int ID,  int iJoystickID,  int iAxesID, const char* szAxesBuffer);
typedef BOOL (PI_FUNC_DECL * PFPI_qJAX)(int ID, const int* iJoystickIDsArray, const int* iAxesIDsArray, int iArraySize, char* szAxesBuffer, int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_qJBS)(int ID, const int* iJoystickIDsArray, const int* iButtonIDsArray, BOOL* pbValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_JDT)(int ID, const int* iJoystickIDsArray, const int* iAxisIDsArray,const int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_JLT)(int ID, int iJoystickID, int iAxisID, int iStartAdress, const double* pdValueArray,int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qJLT)(int ID, const int* iJoystickIDsArray, const int* iAxisIDsArray,  int iNumberOfTables,  int iOffsetOfFirstPointInTable,  int iNumberOfValues, double** pdValueArray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
typedef BOOL (PI_FUNC_DECL * PFPI_JON)(int ID, const int* iJoystickIDsArray, const BOOL* pbValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qJON)(int ID, const int* iJoystickIDsArray, BOOL* pbValueArray, int iArraySize);

/////////////////////////////////////////////////////////////////////////////
// fast scan commands
typedef BOOL (PI_FUNC_DECL * PFPI_AAP)(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dAlignStep, int iNrRepeatedPositions, int iAnalogInput);
typedef BOOL (PI_FUNC_DECL * PFPI_FIO)(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dLinearStep, double dAngleScan, int iAnalogInput);
typedef BOOL (PI_FUNC_DECL * PFPI_FLM)(int ID, const char* szAxis, double dLength, double dThreshold, int iAnalogInput, int iDirection);
typedef BOOL (PI_FUNC_DECL * PFPI_FLS)(int ID, const char* szAxis, double dLength, double dThreshold, int iAnalogInput, int iDirection);
typedef BOOL (PI_FUNC_DECL * PFPI_FSA)(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dDistance, double dAlignStep, int iAnalogInput);
typedef BOOL (PI_FUNC_DECL * PFPI_FSC)(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dDistance, int iAnalogInput);
typedef BOOL (PI_FUNC_DECL * PFPI_FSM)(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dDistance, int iAnalogInput);
typedef BOOL (PI_FUNC_DECL * PFPI_qFSS)(int ID, int* piResult);

/////////////////////////////////////////////////////////////////////////////
// optical boards (hexapod)
typedef BOOL (PI_FUNC_DECL * PFPI_SGA)(int ID, const int* piAnalogChannelIds, const int* piGainValues, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qSGA)(int ID, const int* piAnalogChannelIds, int* piGainValues, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_NAV)(int ID, const int* piAnalogChannelIds, const int* piNrReadingsValues, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qNAV)(int ID, const int* piAnalogChannelIds, int* piNrReadingsValues, int iArraySize);
// more hexapod specific
typedef BOOL (PI_FUNC_DECL * PFPI_GetDynamicMoveBufferSize)(int ID, int *iSize);

/////////////////////////////////////////////////////////////////////////////
// PIShift
typedef BOOL (PI_FUNC_DECL * PFPI_qCOV)(int ID, const int* piChannelsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_MOD)(int ID, const char* szItems, const unsigned int* iModeArray, const char* szValues);
typedef BOOL (PI_FUNC_DECL * PFPI_qMOD)(int ID, const char* szItems, const unsigned int* iModeArray, char* szValues, int iMaxValuesSize);

typedef BOOL (PI_FUNC_DECL * PFPI_qDIA)(int ID, const unsigned int* iIDArray, char* szValues,  int iBufferSize, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHDI)(int ID, char* szBuffer,  int iBufferSize);

/////////////////////////////////////////////////////////////////////////////
// HID
typedef BOOL (PI_FUNC_DECL * PFPI_qHIS)(int ID, char* szBuffer,  int iBufferSize);
typedef BOOL (PI_FUNC_DECL * PFPI_HIS)(int ID, const int* iDeviceIDsArray, const int* iItemIDsArray, const int* iPropertyIDArray, const char* szValues, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHIE)(int ID, const int* iDeviceIDsArray, const int* iAxesIDsArray, double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHIB)(int ID, const int* iDeviceIDsArray, const int* iButtonIDsArray, int* pbValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_HIL)(int ID, const int* iDeviceIDsArray, const int* iLED_IDsArray, const int* pnValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHIL)(int ID, const int* iDeviceIDsArray, const int* iLED_IDsArray, int* pnValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_HIN)(int ID, const char* szAxes, const BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qHIN)(int ID, const char* szAxes, BOOL* pbValueArray);
typedef BOOL (PI_FUNC_DECL * PFPI_HIA)(int ID, const char* szAxes, const int* iFunctionArray, const int* iDeviceIDsArray, const int* iAxesIDsArray);
typedef BOOL (PI_FUNC_DECL * PFPI_qHIA)(int ID, const char* szAxes, const int* iFunctionArray, int* iDeviceIDsArray, int* iAxesIDsArray);
typedef BOOL (PI_FUNC_DECL * PFPI_HDT)(int ID, const int* iDeviceIDsArray, const int* iAxisIDsArray, const int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHDT)(int ID, const int* iDeviceIDsArray, const int* iAxisIDsArray, int* piValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_HIT)(int ID, const int* piTableIdsArray, const int* piPointNumberArray, const double* pdValueArray, int iArraySize);
typedef BOOL (PI_FUNC_DECL * PFPI_qHIT)(int ID, const int* piTableIdsArray,  int iNumberOfTables,  int iOffsetOfFirstPointInTable,  int iNumberOfValues, double** pdValueArray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);

/////////////////////////////////////////////////////////////////////////////
typedef BOOL (PI_FUNC_DECL * PFPI_qMAN)(int ID, const char* szCommand, char* szBuffer,  int iBufferSize);


/////////////////////////////////////////////////////////////////////////////
// Spezial
typedef BOOL (PI_FUNC_DECL * PFPI_GetSupportedFunctions)(int ID, int* piCommandLevelArray, const int iiBufferSize, char* szFunctionNames, const int iMaxFunctioNamesLength);
typedef BOOL (PI_FUNC_DECL * PFPI_GetSupportedParameters)(int ID, int* piParameterIdArray, int* piCommandLevelArray, int* piMemoryLocationArray, int* piDataTypeArray, int* piNumberOfItems, const int iiBufferSize, char* szParameterName, const int iMaxParameterNameSize);
typedef BOOL (PI_FUNC_DECL * PFPI_GetSupportedControllers)(char* szBuffer, int iBufferSize);
typedef int (PI_FUNC_DECL * PFPI_GetAsyncBufferIndex)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_GetAsyncBuffer)(int ID, double** pdValueArray);


typedef BOOL (PI_FUNC_DECL * PFPI_AddStage)(int ID, const char* szAxes);
typedef BOOL (PI_FUNC_DECL * PFPI_RemoveStage)(int ID, const char* szStageName);
typedef BOOL (PI_FUNC_DECL * PFPI_OpenUserStagesEditDialog)(int ID);
typedef BOOL (PI_FUNC_DECL * PFPI_OpenPiStagesEditDialog)(int ID);


///////////////////////////////////////////////////////////////////////////////
// for internal use
typedef BOOL (PI_FUNC_DECL * PFPI_DisableSingleStagesDatFiles)(int ID,BOOL bDisable);
typedef BOOL (PI_FUNC_DECL * PFPI_DisableUserStagesDatFiles)(int ID,BOOL bDisable);


#ifdef __cplusplus
}
#endif
