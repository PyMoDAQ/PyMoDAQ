/////////////////////////////////////////////////////////////////////////////
// This is a part of the PI-Software Sources
// (c)2008-2017 Physik Instrumente (PI) GmbH & Co. KG
// All rights reserved.
/////////////////////////////////////////////////////////////////////////////

//#include <windows.h>


#ifdef __cplusplus
extern "C" {
#endif

#ifdef WIN32
	#undef PI_FUNC_DECL
	#ifdef PI_DLL_EXPORTS
		#ifndef UNKNOWN_GCS_DLL
			#define PI_FUNC_DECL __declspec(dllexport) WINAPI
		#else
			#define PI_FUNC_DECL WINAPI
		#endif
	#else
		#define PI_FUNC_DECL __declspec(dllimport) WINAPI
	#endif
#else
	#ifdef PI_DLL_EXPORTS
		#define PI_FUNC_DECL __attribute__ ((visibility("default")))
	#else
		#define PI_FUNC_DECL
	#endif
#endif


#ifndef WIN32
#ifndef PI_IOS
	#include <inttypes.h>
	
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

#endif //PI_IOS
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
int	PI_FUNC_DECL PI_InterfaceSetupDlg(const char* szRegKeyName);
int PI_FUNC_DECL PI_ConnectRS232(int nPortNr, int iBaudRate);
int PI_FUNC_DECL PI_TryConnectRS232(int port, int baudrate);
int PI_FUNC_DECL PI_TryConnectUSB(const char* szDescription);
BOOL PI_FUNC_DECL PI_IsConnecting(int threadID, BOOL* bCOnnecting);
int PI_FUNC_DECL PI_GetControllerID(int threadID);
BOOL PI_FUNC_DECL PI_CancelConnect(int threadID);

int 	PI_FUNC_DECL	PI_OpenRS232DaisyChain(int iPortNumber, int iBaudRate, int* pNumberOfConnectedDaisyChainDevices, char* szDeviceIDNs, int iBufferSize);
int 	PI_FUNC_DECL	PI_ConnectDaisyChainDevice(int iPortId, int iDeviceNumber);
void 	PI_FUNC_DECL	PI_CloseDaisyChain(int iPortId);
#ifndef WIN32
int 	PI_FUNC_DECL	PI_ConnectRS232ByDevName(const char* szDevName, int BaudRate);
int 	PI_FUNC_DECL	PI_OpenRS232DaisyChainByDevName(const char* szDevName, int iBaudRate, int* pNumberOfConnectedDaisyChainDevices, char* szDeviceIDNs, int iBufferSize);
#endif

int	    PI_FUNC_DECL	PI_ConnectNIgpib(int nBoard, int nDevAddr);

int	    PI_FUNC_DECL	PI_ConnectTCPIP(const char* szHostname, int port);
int	    PI_FUNC_DECL	PI_EnableTCPIPScan(int iMask);
int	    PI_FUNC_DECL	PI_EnumerateTCPIPDevices(char* szBuffer, int iBufferSize, const char* szFilter);
int	    PI_FUNC_DECL	PI_ConnectTCPIPByDescription(const char* szDescription);
int 	PI_FUNC_DECL	PI_OpenTCPIPDaisyChain(const char* szHostname, int port, int* pNumberOfConnectedDaisyChainDevices, char* szDeviceIDNs, int iBufferSize);

int	    PI_FUNC_DECL	PI_EnumerateUSB(char* szBuffer, int iBufferSize, const char* szFilter);
int	    PI_FUNC_DECL	PI_ConnectUSB(const char* szDescription);
int	    PI_FUNC_DECL	PI_ConnectUSBWithBaudRate(const char* szDescription,int iBaudRate);
int 	PI_FUNC_DECL	PI_OpenUSBDaisyChain(const char* szDescription, int* pNumberOfConnectedDaisyChainDevices, char* szDeviceIDNs, int iBufferSize);

BOOL	PI_FUNC_DECL	PI_IsConnected(int ID);
void	PI_FUNC_DECL	PI_CloseConnection(int ID);
int	    PI_FUNC_DECL	PI_GetError(int ID);
BOOL	PI_FUNC_DECL	PI_SetErrorCheck(int ID, BOOL bErrorCheck);
BOOL	PI_FUNC_DECL	PI_TranslateError(int errNr, char* szBuffer, int iBufferSize);
int	    PI_FUNC_DECL	PI_SetTimeout(int ID, int timeoutInMS);

int		PI_FUNC_DECL	PI_SetDaisyChainScanMaxDeviceID(int maxID);

BOOL	PI_FUNC_DECL	PI_EnableReconnect(int ID, BOOL bEnable);
int     PI_FUNC_DECL    PI_SetNrTimeoutsBeforeClose(int ID, int nrTimeoutsBeforeClose);

BOOL    PI_FUNC_DECL    PI_GetInterfaceDescription(int ID, char* szBuffer, int iBufferSize);


/////////////////////////////////////////////////////////////////////////////
// general
BOOL PI_FUNC_DECL PI_qERR(int ID, int* pnError);
BOOL PI_FUNC_DECL PI_qIDN(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_INI(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_qHLP(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qHPA(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qHPV(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qCSV(int ID, double* pdCommandSyntaxVersion);
BOOL PI_FUNC_DECL PI_qOVF(int ID, const char* szAxes, BOOL* piValueArray);
BOOL PI_FUNC_DECL PI_RBT(int ID);
BOOL PI_FUNC_DECL PI_REP(int ID);
BOOL PI_FUNC_DECL PI_BDR(int ID, int iBaudRate);
BOOL PI_FUNC_DECL PI_qBDR(int ID, int* iBaudRate);
BOOL PI_FUNC_DECL PI_DBR(int ID, int iBaudRate);
BOOL PI_FUNC_DECL PI_qDBR(int ID, int* iBaudRate);
BOOL PI_FUNC_DECL PI_qVER(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qSSN(int ID, char* szSerialNumber, int iBufferSize);
BOOL PI_FUNC_DECL PI_CCT(int ID, int iCommandType);
BOOL PI_FUNC_DECL PI_qCCT(int ID, int *iCommandType);
BOOL PI_FUNC_DECL PI_qTVI(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_IFC(int ID, const char* szParameters, const char* szValues);
BOOL PI_FUNC_DECL PI_qIFC(int ID, const char* szParameters, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_IFS(int ID, const char* szPassword, const char* szParameters, const char* szValues);
BOOL PI_FUNC_DECL PI_qIFS(int ID, const char* szParameters, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qECO(int ID, const char* szSendString, char* szValues, int iBufferSize);

BOOL PI_FUNC_DECL PI_MOV(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qMOV(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_MVR(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_MVE(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_POS(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qPOS(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_IsMoving(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_HLT(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_STP(int ID);
BOOL PI_FUNC_DECL PI_StopAll(int ID);
BOOL PI_FUNC_DECL PI_qONT(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_RTO(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_qRTO(int ID, const char* szAxes, int* piValueArray);
BOOL PI_FUNC_DECL PI_ATZ(int ID, const char* szAxes, const double* pdLowvoltageArray, const BOOL* pfUseDefaultArray);
BOOL PI_FUNC_DECL PI_qATZ(int ID, const char* szAxes, int* piAtzResultArray);
BOOL PI_FUNC_DECL PI_AOS(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qAOS(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_HasPosChanged(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_GetErrorStatus(int ID, BOOL* pbIsReferencedArray, BOOL* pbIsReferencing, BOOL* pbIsMovingArray, BOOL* pbIsMotionErrorArray);


BOOL PI_FUNC_DECL PI_SVA(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qSVA(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_SVR(int ID, const char* szAxes, const double* pdValueArray);

BOOL PI_FUNC_DECL PI_DFH(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_qDFH(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_GOH(int ID, const char* szAxes);

BOOL PI_FUNC_DECL PI_qCST(int ID, const char* szAxes, char* szNames, int iBufferSize);
BOOL PI_FUNC_DECL PI_CST(int ID, const char* szAxes, const char* szNames);
BOOL PI_FUNC_DECL PI_qVST(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qPUN(int ID, const char* szAxes, char* szUnit, int iBufferSize);

BOOL PI_FUNC_DECL PI_EAX(int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qEAX(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_SVO(int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qSVO(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_SMO( int ID, const char*  szAxes, const int* piValueArray);
BOOL PI_FUNC_DECL PI_qSMO(int ID, const char* szAxes, int* piValueArray);
BOOL PI_FUNC_DECL PI_DCO(int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qDCO(int ID, const char* szAxes, BOOL* pbValueArray);

BOOL PI_FUNC_DECL PI_BRA(int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qBRA(int ID, const char* szAxes, BOOL* pbValueArray);

BOOL PI_FUNC_DECL PI_RON(int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qRON(int ID, const char* szAxes, BOOL* pbValueArray);

BOOL PI_FUNC_DECL PI_VEL(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qVEL(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_JOG(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qJOG(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_qTCV(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_VLS(int ID, double dSystemVelocity);
BOOL PI_FUNC_DECL PI_qVLS(int ID, double* pdSystemVelocity);

BOOL PI_FUNC_DECL PI_ACC(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qACC(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_DEC(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qDEC(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_VCO(int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qVCO(int ID, const char* szAxes, BOOL* pbValueArray);

BOOL PI_FUNC_DECL PI_SPA(int ID, const char* szItems, const unsigned int* iParameterArray, const double* pdValueArray, const char* szStrings);
BOOL PI_FUNC_DECL PI_qSPA(int ID, const char* szItems, unsigned int* iParameterArray, double* pdValueArray, char* szStrings, int iMaxNameSize);
BOOL PI_FUNC_DECL PI_SEP(int ID, const char* szPassword, const char* szItems, const unsigned int* iParameterArray, const double* pdValueArray, const char* szStrings);
BOOL PI_FUNC_DECL PI_qSEP(int ID, const char* szItems, unsigned int* iParameterArray, double* pdValueArray, char* szStrings, int iMaxNameSize);
BOOL PI_FUNC_DECL PI_WPA(int ID, const char* szPassword, const char* szItems, const unsigned int* iParameterArray);
BOOL PI_FUNC_DECL PI_DPA(int ID, const char* szPassword, const char*  szItems, const unsigned int* iParameterArray);
BOOL PI_FUNC_DECL PI_TIM(int ID, double dTimer);
BOOL PI_FUNC_DECL PI_qTIM(int ID, double* pdTimer);
BOOL PI_FUNC_DECL PI_RPA(int ID, const char* szItems, const unsigned int* iParameterArray);
BOOL PI_FUNC_DECL PI_SPA_String(int ID, const char* szItems, const unsigned int* iParameterArray, const char* szStrings);
BOOL PI_FUNC_DECL PI_qSPA_String(int ID, const char* szItems, const unsigned int* iParameterArray, char* szStrings, int iMaxNameSize);
BOOL PI_FUNC_DECL PI_SEP_String(int ID, const char* szPassword, const char* szItems, const unsigned int* iParameterArray, const char* szStrings);
BOOL PI_FUNC_DECL PI_qSEP_String(int ID, const char* szItems, unsigned int* iParameterArray, char* szStrings, int iMaxNameSize);
BOOL PI_FUNC_DECL PI_SPA_int64(int ID, const char* szItems, const unsigned int* iParameterArray, const __int64* piValueArray);
BOOL PI_FUNC_DECL PI_qSPA_int64(int ID, const char* szItems, unsigned int* iParameterArray, __int64* piValueArray);
BOOL PI_FUNC_DECL PI_SEP_int64(int ID, const char* szPassword, const char* szItems, const unsigned int* iParameterArray, const __int64* piValueArray);
BOOL PI_FUNC_DECL PI_qSEP_int64(int ID, const char* szItems, unsigned int* iParameterArray, __int64* piValueArray);

BOOL PI_FUNC_DECL PI_STE(int ID, const char* szAxes, const double* dOffsetArray);
BOOL PI_FUNC_DECL PI_qSTE(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_IMP(int ID, const char*  szAxes, const double* pdImpulseSize);
BOOL PI_FUNC_DECL PI_IMP_PulseWidth(int ID, char cAxis, double dOffset, int iPulseWidth);
BOOL PI_FUNC_DECL PI_qIMP(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_SAI(int ID, const char* szOldAxes, const char* szNewAxes);
BOOL PI_FUNC_DECL PI_qSAI(int ID, char* szAxes, int iBufferSize);
BOOL PI_FUNC_DECL PI_qSAI_ALL(int ID, char* szAxes, int iBufferSize);

BOOL PI_FUNC_DECL PI_CCL(int ID, int iComandLevel, const char* szPassWord);
BOOL PI_FUNC_DECL PI_qCCL(int ID, int* piComandLevel);

BOOL PI_FUNC_DECL PI_AVG(int ID, int iAverrageTime);
BOOL PI_FUNC_DECL PI_qAVG(int ID, int *iAverrageTime);

BOOL PI_FUNC_DECL PI_qHAR(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qLIM(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qTRS(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_FNL(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_qFPH(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_FPH(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_FPL(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_FRF(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_FED(int ID, const char* szAxes, const int* piEdgeArray, const int* piParamArray);
BOOL PI_FUNC_DECL PI_qFRF(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_DIO(int ID, const int* piChannelsArray, const BOOL* pbValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qDIO(int ID, const int* piChannelsArray, BOOL* pbValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTIO(int ID, int* piInputNr, int* piOutputNr);
BOOL PI_FUNC_DECL PI_IsControllerReady(int ID, int* piControllerReady);
BOOL PI_FUNC_DECL PI_qSRG(int ID, const char* szAxes, const int* iRegisterArray, int* iValArray);

BOOL PI_FUNC_DECL PI_ATC(int ID, const int* piChannels, const int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qATC(int ID, const int* piChannels, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qATS(int ID, const int* piChannels, const int* piOptions, int* piValueArray, int iArraySize);

BOOL PI_FUNC_DECL PI_SPI(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qSPI(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_SCT(int ID, double dCycleTime);
BOOL PI_FUNC_DECL PI_qSCT(int ID, double* pdCycleTime);

BOOL PI_FUNC_DECL PI_SST(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qSST(int ID, const char* szAxes, double* pdValueArray);

BOOL PI_FUNC_DECL PI_qCTV(int ID, const char* szAxes, double* pdValarray);
BOOL PI_FUNC_DECL PI_CTV(int ID, const char* szAxes, const double* pdValarray);
BOOL PI_FUNC_DECL PI_CTR(int ID, const char* szAxes, const double* pdValarray);
BOOL PI_FUNC_DECL PI_qCAV(int ID, const char* szAxes, double* pdValarray);
BOOL PI_FUNC_DECL PI_qCCV(int ID, const char* szAxes, double* pdValarray);
BOOL PI_FUNC_DECL PI_qCMO(int ID, const char* szAxes, int* piValArray);
BOOL PI_FUNC_DECL PI_CMO(int ID, const char* szAxes, const int* piValArray);

/////////////////////////////////////////////////////////////////////////////
// Macro commands
BOOL PI_FUNC_DECL PI_IsRunningMacro(int ID, BOOL* pbRunningMacro);
BOOL PI_FUNC_DECL PI_MAC_BEG(int ID, const char* szMacroName);
BOOL PI_FUNC_DECL PI_MAC_START(int ID, const char* szMacroName);
BOOL PI_FUNC_DECL PI_MAC_NSTART(int ID, const char* szMacroName, int nrRuns);

BOOL PI_FUNC_DECL PI_MAC_START_Args(int ID, const char* szMacroName, const char* szArgs);
BOOL PI_FUNC_DECL PI_MAC_NSTART_Args(int ID, const char* szMacroName, int nrRuns, const char* szArgs);
BOOL PI_FUNC_DECL PI_MAC_END(int ID);
BOOL PI_FUNC_DECL PI_MAC_DEL(int ID, const char* szMacroName);
BOOL PI_FUNC_DECL PI_MAC_DEF(int ID, const char* szMacroName);
BOOL PI_FUNC_DECL PI_MAC_qDEF(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_MAC_qERR(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_MAC_qFREE(int ID, int* iFreeSpace);
BOOL PI_FUNC_DECL PI_qMAC(int ID, const char* szMacroName, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qRMC(int ID, char* szBuffer, int iBufferSize);

BOOL PI_FUNC_DECL PI_DEL(int ID, int nMilliSeconds);
BOOL PI_FUNC_DECL PI_WAC(int ID, const char* szCondition);
BOOL PI_FUNC_DECL PI_MEX(int ID, const char* szCondition);

BOOL PI_FUNC_DECL PI_VAR(int ID, const char* szVariable, const char* szValue);
BOOL PI_FUNC_DECL PI_qVAR(int ID, const char* szVariables, char* szValues,  int iBufferSize);
BOOL PI_FUNC_DECL PI_ADD(int ID, const char* szVariable, double value1, double value2);
BOOL PI_FUNC_DECL PI_CPY(int ID, const char* szVariable, const char* szCommand);

/////////////////////////////////////////////////////////////////////////////
// String commands.
BOOL PI_FUNC_DECL PI_GcsCommandset(int ID, const char* szCommand);
BOOL PI_FUNC_DECL PI_GcsGetAnswer(int ID, char* szAnswer, int iBufferSize);
BOOL PI_FUNC_DECL PI_GcsGetAnswerSize(int ID, int* iAnswerSize);


/////////////////////////////////////////////////////////////////////////////
// limits
BOOL PI_FUNC_DECL PI_qTMN(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_qTMX(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_NLM(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qNLM(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_PLM(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qPLM(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_SSL(int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qSSL(int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qVMO(int ID, const char* szAxes, const double* pdValarray, BOOL* pbMovePossible);
BOOL PI_FUNC_DECL PI_qCMN(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_qCMX(int ID, const char* szAxes, double* pdValueArray);


/////////////////////////////////////////////////////////////////////////////
// Wave commands.
BOOL PI_FUNC_DECL PI_IsGeneratorRunning(int ID, const int* piWaveGeneratorIds, BOOL* pbValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTWG(int ID, int* piWaveGenerators);
BOOL PI_FUNC_DECL PI_WAV_SIN_P(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iCenterPointOfWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
BOOL PI_FUNC_DECL PI_WAV_LIN(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iNumberOfSpeedUpDownPointsInWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
BOOL PI_FUNC_DECL PI_WAV_NOISE(int ID, int iWaveTableId, int iAddAppendWave, double dAmplitudeOfWave, double dOffsetOfWave,int iSegmentLength);   
BOOL PI_FUNC_DECL PI_WAV_SWEEP(int ID, int  iWaveTableId, int iAddAppendWave, unsigned int iStarFequencytValueInPoints, unsigned int iStopFrequencyValueInPoints, unsigned int nLengthOfWave, double dAmplitudeOfWave, double dOffsetOfWave);
BOOL PI_FUNC_DECL PI_WAV_RAMP(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iCenterPointOfWave, int iNumberOfSpeedUpDownPointsInWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
BOOL PI_FUNC_DECL PI_WAV_PNT(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, const double* pdWavePoints);
BOOL PI_FUNC_DECL PI_qWAV(int ID, const int* piWaveTableIdsArray, const int* piParamereIdsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_WGO(int ID, const int* piWaveGeneratorIdsArray, const int* iStartModArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWGO(int ID, const int* piWaveGeneratorIdsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_WGC(int ID, const int* piWaveGeneratorIdsArray, const int* piNumberOfCyclesArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWGC(int ID, const int* piWaveGeneratorIdsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWGI(int ID, const int* piWaveGeneratorIdsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWGN(int ID, const int* piWaveGeneratorIdsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWGS(int ID, int iWaveGeneratorId, const char* szItem, char* buffer, int bufferSize);
BOOL PI_FUNC_DECL PI_WSL(int ID, const int* piWaveGeneratorIdsArray, const int* piWaveTableIdsArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWSL(int ID, const int* piWaveGeneratorIdsArray, int* piWaveTableIdsArray, int iArraySize);
BOOL PI_FUNC_DECL PI_DTC(int ID, const int* piDdlTableIdsArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qDTL(int ID, const int* piDdlTableIdsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_WCL(int ID, const int* piWaveTableIdsArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTLT(int ID, int* piNumberOfDdlTables);
BOOL PI_FUNC_DECL PI_qGWD_SYNC(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfValues, double* pdValueArray);
BOOL PI_FUNC_DECL PI_qGWD(int ID, const int* iWaveTableIdsArray, int iNumberOfWaveTables, int iOffset, int nrValues, double** pdValarray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
BOOL PI_FUNC_DECL PI_WOS(int ID, const int* iWaveTableIdsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWOS(int ID, const int* iWaveTableIdsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_WTR(int ID, const int* piWaveGeneratorIdsArray, const int* piTableRateArray, const int* piInterpolationTypeArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qWTR(int ID, const int* piWaveGeneratorIdsArray, int* piTableRateArray, int* piInterpolationTypeArray, int iArraySize);
BOOL PI_FUNC_DECL PI_DDL(int ID, int iDdlTableId,  int iOffsetOfFirstPointInDdlTable,  int iNumberOfValues, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qDDL_SYNC(int ID,  int iDdlTableId,  int iOffsetOfFirstPointInDdlTable,  int iNumberOfValues, double* pdValueArray);
BOOL PI_FUNC_DECL PI_qDDL(int ID, const int* iDdlTableIdsArray, int iNumberOfDdlTables, int iOffset, int nrValues, double** pdValarray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
BOOL PI_FUNC_DECL PI_DPO(int ID, const char* szAxes);
BOOL PI_FUNC_DECL PI_qWMS(int ID, const int* piWaveTableIds, int* iWaveTableMaximumSize, int iArraySize);
BOOL PI_FUNC_DECL PI_TWE(int ID, const int* piWaveTableIdsArray, const int* piWaveTableStartIndexArray, const int* piWaveTableEndIndexArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTWE(int ID, const int* piWaveTableIdsArray, int* piWaveTableStartIndexArray, int* piWaveTableEndIndexArray, int iArraySize);



///////////////////////////////////////////////////////////////////////////////
//// Trigger commands.
BOOL PI_FUNC_DECL PI_TWC(int ID);
BOOL PI_FUNC_DECL PI_TWS(int ID, const int* piTriggerChannelIdsArray, const int* piPointNumberArray, const int* piSwitchArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTWS(int ID, const int* iTriggerChannelIdsArray, int iNumberOfTriggerChannels, int iOffset, int nrValues, double** pdValarray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
BOOL PI_FUNC_DECL PI_CTO(int ID, const int* piTriggerOutputIds, const int* piTriggerParameterArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_CTOString(int ID, const int* piTriggerOutputIds, const int* piTriggerParameterArray, const char* szValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qCTO(int ID, const int* piTriggerOutputIds, const int* piTriggerParameterArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qCTOString(int ID, const int* piTriggerOutputIds, const int* piTriggerParameterArray, char* szValueArray, int iArraySize, int iBufferSize);
BOOL PI_FUNC_DECL PI_TRO(int ID, const int* piTriggerOutputIds, const BOOL* pbTriggerState, int iArraySize);
BOOL PI_FUNC_DECL PI_qTRO(int ID, const int* piTriggerOutputIds, BOOL* pbTriggerState, int iArraySize);
BOOL PI_FUNC_DECL PI_TRI(int ID, const int* piTriggerInputIds, const BOOL* pbTriggerState, int iArraySize);
BOOL PI_FUNC_DECL PI_qTRI(int ID, const int* piTriggerInputIds, BOOL* pbTriggerState, int iArraySize);
BOOL PI_FUNC_DECL PI_CTI(int ID, const int* piTriggerInputIds, const int* piTriggerParameterArray, const char* szValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qCTI(int ID, const int* piTriggerInputIds, const int* piTriggerParameterArray, char* szValueArray, int iArraySize, int iBufferSize);


/////////////////////////////////////////////////////////////////////////////
// Record table commands.
BOOL PI_FUNC_DECL PI_qHDR(int ID, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qTNR(int ID, int* piNumberOfRecordCannels);
BOOL PI_FUNC_DECL PI_DRC(int ID, const int* piRecordTableIdsArray, const char* szRecordSourceIds, const int* piRecordOptionArray);
BOOL PI_FUNC_DECL PI_qDRC(int ID, const int* piRecordTableIdsArray, char* szRecordSourceIds, int* piRecordOptionArray, int iRecordSourceIdsBufferSize, int iRecordOptionArraySize);
BOOL PI_FUNC_DECL PI_qDRR_SYNC(int ID,  int iRecordTablelId,  int iOffsetOfFirstPointInRecordTable,  int iNumberOfValues, double* pdValueArray);
BOOL PI_FUNC_DECL PI_qDRR(int ID, const int* piRecTableIdIdsArray,  int iNumberOfRecTables,  int iOffsetOfFirstPointInRecordTable,  int iNumberOfValues, double** pdValueArray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
BOOL PI_FUNC_DECL PI_DRT(int ID, const int* piRecordChannelIdsArray, const int* piTriggerSourceArray, const char* szValues, int iArraySize);
BOOL PI_FUNC_DECL PI_qDRT(int ID, const int* piRecordChannelIdsArray, int* piTriggerSourceArray, char* szValues, int iArraySize, int iValueBufferLength);
BOOL PI_FUNC_DECL PI_RTR(int ID, int piReportTableRate);
BOOL PI_FUNC_DECL PI_qRTR(int ID, int* piReportTableRate);
BOOL PI_FUNC_DECL PI_WGR(int ID);
BOOL PI_FUNC_DECL PI_qDRL(int ID, const int* piRecordChannelIdsArray, int* piNuberOfRecordedValuesArray, int iArraySize);

//////////////////////////////////////////////////////////////////////////
// System Response commands
BOOL PI_FUNC_DECL PI_qGFL(int ID, int* piNumberOfRecordedFrequencyMeasurements);
BOOL PI_FUNC_DECL PI_qGFR(int ID, const int* piTableIdsArray, int iNumberOfTables, int iOffsetOfFirstPointInTable,  int iNumberOfValues, double** pdValueArray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
BOOL PI_FUNC_DECL PI_WFR(int ID, const char *szAxis, double dPos, int iSource, double dAmpl, double dLowFrq, double dHighFrq, int iSweepSteps, int iSweepMode, double dVelOffset);
BOOL PI_FUNC_DECL PI_qWFR(int ID, char* szBuffer, int iBufferSize);


/////////////////////////////////////////////////////////////////////////////
// Piezo-Channel commands.
BOOL PI_FUNC_DECL PI_VMA(int ID, const int* piPiezoChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qVMA(int ID, const int* piPiezoChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_VMI(int ID, const int* piPiezoChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qVMI(int ID, const int* piPiezoChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_VOL(int ID, const int* piPiezoChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qVOL(int ID, const int* piPiezoChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTPC(int ID, int* piNumberOfPiezoChannels);
BOOL PI_FUNC_DECL PI_ONL(int ID, const int* iPiezoCannels, const int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qONL(int ID, const int* iPiezoCannels, int* piValueArray, int iArraySize);


/////////////////////////////////////////////////////////////////////////////
// Sensor-Channel commands.
BOOL PI_FUNC_DECL PI_qTAD(int ID, const int* piSensorsChannelsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTNS(int ID, const int* piSensorsChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_TSP(int ID, const int* piSensorsChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTSP(int ID, const int* piSensorsChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_SCN(int ID, const int* piSensorsChannelsArray, const int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qSCN(int ID, const int* piSensorsChannelsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTSC(int ID, int* piNumberOfSensorChannels);


/////////////////////////////////////////////////////////////////////////////
// PIEZOWALK(R)-Channel commands.
BOOL PI_FUNC_DECL PI_APG(int ID, const int* piPIEZOWALKChannelsArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qAPG(int ID, const int* piPIEZOWALKChannelsArray, int* piValueArray, int iArraySize);

BOOL PI_FUNC_DECL PI_OAC(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOAC(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_OAD(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOAD(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_ODC(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qODC(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_OCD(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOCD(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_OSM(int ID, const int* piPIEZOWALKChannelsArray, const int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOSM(int ID, const int* piPIEZOWALKChannelsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_OSMf(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOSMf(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_OSMstringIDs(int ID, const char* szAxisOrChannelIds, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qOSMstringIDs(int ID, const char* szAxisOrChannelIds, double* pdValueArray);
BOOL PI_FUNC_DECL PI_OVL(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOVL(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOSN(int ID, const int* piPIEZOWALKChannelsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qOSNstringIDs(int ID, const char* szAxisOrChannelIds, int* piValueArray);
BOOL PI_FUNC_DECL PI_SSA(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qSSA(int ID, const int* piPIEZOWALKChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_RNP(int ID, const int* piPIEZOWALKChannelsArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_PGS(int ID, const int* piPIEZOWALKChannelsArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTAC(int ID, int* pnNrChannels);
BOOL PI_FUNC_DECL PI_qTAV(int ID, const int* piChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_OMA(int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qOMA(int ID, const char* szAxes, double* pdValueArray);
BOOL PI_FUNC_DECL PI_OMR(int ID, const char* szAxes, const double* pdValueArray);

/////////////////////////////////////////////////////////////////////////////
// Joystick
BOOL PI_FUNC_DECL PI_qJAS(int ID, const int* iJoystickIDsArray, const int* iAxesIDsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_JAX(int ID,  int iJoystickID,  int iAxesID, const char* szAxesBuffer);
BOOL PI_FUNC_DECL PI_qJAX(int ID, const int* iJoystickIDsArray, const int* iAxesIDsArray, int iArraySize, char* szAxesBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qJBS(int ID, const int* iJoystickIDsArray, const int* iButtonIDsArray, BOOL* pbValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_JDT(int ID, const int* iJoystickIDsArray, const int* iAxisIDsArray,const int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_JLT(int ID, int iJoystickID, int iAxisID, int iStartAdress, const double* pdValueArray,int iArraySize);
BOOL PI_FUNC_DECL PI_qJLT(int ID, const int* iJoystickIDsArray, const int* iAxisIDsArray,  int iNumberOfTables,  int iOffsetOfFirstPointInTable,  int iNumberOfValues, double** pdValueArray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
BOOL PI_FUNC_DECL PI_JON(int ID, const int* iJoystickIDsArray, const BOOL* pbValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qJON(int ID, const int* iJoystickIDsArray, BOOL* pbValueArray, int iArraySize);

/////////////////////////////////////////////////////////////////////////////
// fast scan commands
BOOL PI_FUNC_DECL PI_AAP(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dAlignStep, int iNrRepeatedPositions, int iAnalogInput);
BOOL PI_FUNC_DECL PI_FIO(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dLinearStep, double dAngleScan, int iAnalogInput);
BOOL PI_FUNC_DECL PI_FLM(int ID, const char* szAxis, double dLength, double dThreshold, int iAnalogInput, int iDirection);
BOOL PI_FUNC_DECL PI_FLS(int ID, const char* szAxis, double dLength, double dThreshold, int iAnalogInput, int iDirection);
BOOL PI_FUNC_DECL PI_FSA(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dDistance, double dAlignStep, int iAnalogInput);
BOOL PI_FUNC_DECL PI_FSC(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dDistance, int iAnalogInput);
BOOL PI_FUNC_DECL PI_FSM(int ID, const char* szAxis1, double dLength1, const char* szAxis2, double dLength2, double dThreshold, double dDistance, int iAnalogInput);
BOOL PI_FUNC_DECL PI_qFSS(int ID, int* piResult);

BOOL PI_FUNC_DECL PI_FGC(int ID, const char* szProcessIds, const double* pdScanAxisCenterValueArray, const double* pdStepAxisCenterValueArray);
BOOL PI_FUNC_DECL PI_qFGC(int ID, const char* szProcessIds, double* pdScanAxisCenterValueArray, double* pdStepAxisCenterValueArray);
BOOL PI_FUNC_DECL PI_FRC(int ID, const char* szProcessIdBase, const char* szProcessIdsCoupled);
BOOL PI_FUNC_DECL PI_qFRC(int ID, const char* szProcessIdsBase, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_qTCI(int ID, const int* piFastAlignmentInputIdsArray, double* pdCalculatedInputValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_SIC(int ID, int iFastAlignmentInputId, int iCalcType, const double* pdParameters, int iNumberOfParameters);
BOOL PI_FUNC_DECL PI_qSIC(int ID, const int* piFastAlignmentInputIdsArray, int iNumberOfInputIds, char* szBuffer, int iBufferSize);
BOOL PI_FUNC_DECL PI_FDR(int ID, const char* szScanRoutineName, const char* szScanAxis, const double dScanAxisRange, const char* szStepAxis, const double dStepAxisRange, const char* szParameters);
BOOL PI_FUNC_DECL PI_FDG(int ID, const char* szScanRoutineName, const char* szScanAxis, const char* szStepAxis, const char* szParameters);
BOOL PI_FUNC_DECL PI_FRS(int ID, const char* szScanRoutineNames);
BOOL PI_FUNC_DECL PI_FRP(int ID, const char* szScanRoutineNames, const int* piOptionsArray);
BOOL PI_FUNC_DECL PI_qFRP(int ID, const char* szScanRoutineNames, int* piOptionsArray);
BOOL PI_FUNC_DECL PI_qFRR(int ID, const char* szScanRoutineNames, int iResultId, char* szResult, int iBufferSize);
BOOL PI_FUNC_DECL PI_qFRRArray(int ID, const char* szScanRoutineNames, const int* iResultIds, char* szResult, int iBufferSize);
BOOL PI_FUNC_DECL PI_qFRH(int ID, char* szBuffer, int iBufferSize);

/////////////////////////////////////////////////////////////////////////////
// optical boards (hexapod)
BOOL PI_FUNC_DECL PI_SGA(int ID, const int* piAnalogChannelIds, const int* piGainValues, int iArraySize);
BOOL PI_FUNC_DECL PI_qSGA(int ID, const int* piAnalogChannelIds, int* piGainValues, int iArraySize);
BOOL PI_FUNC_DECL PI_NAV(int ID, const int* piAnalogChannelIds, const int* piNrReadingsValues, int iArraySize);
BOOL PI_FUNC_DECL PI_qNAV(int ID, const int* piAnalogChannelIds, int* piNrReadingsValues, int iArraySize);
// more hexapod specific
BOOL	PI_FUNC_DECL	PI_GetDynamicMoveBufferSize(int ID, int *iSize);

/////////////////////////////////////////////////////////////////////////////
// PIShift
BOOL PI_FUNC_DECL PI_qCOV(int ID, const int* piChannelsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_MOD(int ID, const char* szItems, const unsigned int* iModeArray, const char* szValues);
BOOL PI_FUNC_DECL PI_qMOD(int ID, const char* szItems, const unsigned int* iModeArray, char* szValues, int iMaxValuesSize);

BOOL PI_FUNC_DECL PI_qDIA(int ID, const unsigned int* iIDArray, char* szValues,  int iBufferSize, int iArraySize);
BOOL PI_FUNC_DECL PI_qHDI(int ID, char* szBuffer,  int iBufferSize);

/////////////////////////////////////////////////////////////////////////////
// HID
BOOL PI_FUNC_DECL PI_qHIS (int ID, char* szBuffer,  int iBufferSize);
BOOL PI_FUNC_DECL PI_HIS  (int ID, const int* iDeviceIDsArray, const int* iItemIDsArray, const int* iPropertyIDArray, const char* szValues, int iArraySize);
BOOL PI_FUNC_DECL PI_qHIE (int ID, const int* iDeviceIDsArray, const int* iAxesIDsArray, double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qHIB (int ID, const int* iDeviceIDsArray, const int* iButtonIDsArray, int* pbValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_HIL  (int ID, const int* iDeviceIDsArray, const int* iLED_IDsArray, const int* pnValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qHIL (int ID, const int* iDeviceIDsArray, const int* iLED_IDsArray, int* pnValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_HIN  (int ID, const char* szAxes, const BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_qHIN (int ID, const char* szAxes, BOOL* pbValueArray);
BOOL PI_FUNC_DECL PI_HIA  (int ID, const char* szAxes, const int* iFunctionArray, const int* iDeviceIDsArray, const int* iAxesIDsArray);
BOOL PI_FUNC_DECL PI_qHIA (int ID, const char* szAxes, const int* iFunctionArray, int* iDeviceIDsArray, int* iAxesIDsArray);
BOOL PI_FUNC_DECL PI_HDT  (int ID, const int* iDeviceIDsArray, const int* iAxisIDsArray, const int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qHDT (int ID, const int* iDeviceIDsArray, const int* iAxisIDsArray, int* piValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_HIT  (int ID, const int* piTableIdsArray, const int* piPointNumberArray, const double* pdValueArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qHIT (int ID, const int* piTableIdsArray,  int iNumberOfTables,  int iOffsetOfFirstPointInTable,  int iNumberOfValues, double** pdValueArray, char* szGcsArrayHeader, int iGcsArrayHeaderMaxSize);

/////////////////////////////////////////////////////////////////////////////
BOOL PI_FUNC_DECL PI_qMAN(int ID, const char* szCommand, char* szBuffer,  int iBufferSize);

/////////////////////////////////////////////////////////////////////////////
BOOL PI_FUNC_DECL PI_KSF  (int ID, const char* szNameOfCoordSystem);
BOOL PI_FUNC_DECL PI_KEN  (int ID, const char* szNameOfCoordSystem);
BOOL PI_FUNC_DECL PI_KRM  (int ID, const char* szNameOfCoordSystem);
BOOL PI_FUNC_DECL PI_KLF  (int ID, const char* szNameOfCoordSystem);
BOOL PI_FUNC_DECL PI_KSD  (int ID, const char* szNameOfCoordSystem, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_KST  (int ID, const char* szNameOfCoordSystem, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_KSW  (int ID, const char* szNameOfCoordSystem, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_KLD  (int ID, const char* szNameOfCoordSystem, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_KSB  (int ID, const char* szNameOfCoordSystem, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_MRT  (int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_MRW  (int ID, const char* szAxes, const double* pdValueArray);
BOOL PI_FUNC_DECL PI_qKLT (int ID, const char* szStartCoordSystem, const char* szEndCoordSystem, char* buffer, int bufsize);
BOOL PI_FUNC_DECL PI_qKEN (int ID, const char* szNamesOfCoordSystems, char* buffer, int bufsize);
BOOL PI_FUNC_DECL PI_qKET (int ID, const char* szTypes, char* buffer, int bufsize);
BOOL PI_FUNC_DECL PI_qKLS (int ID, const char* szNameOfCoordSystem, const char* szItem1, const char* szItem2, char* buffer, int bufsize);
BOOL PI_FUNC_DECL PI_KLN  (int ID, const char* szNameOfChild, const char* szNameOfParent);
BOOL PI_FUNC_DECL PI_qKLN (int ID, const char* szNamesOfCoordSystems, char* buffer, int bufsize);
BOOL PI_FUNC_DECL PI_qTRA (int ID, const char* szAxes, const double* pdComponents, double* pdValueArray);
BOOL PI_FUNC_DECL PI_qKLC (int ID, const char* szNameOfCoordSystem1, const char* szNameOfCoordSystem2, const char* szItem1, const char* szItem2, char* buffer, int bufsize);
BOOL PI_FUNC_DECL PI_KCP  (int ID, const char* szSource, const char* szDestination);


/////////////////////////////////////////////////////////////////////////////
// Trajectory
BOOL PI_FUNC_DECL PI_TGA(int ID, const int* piTrajectoriesArray, const double* pdValarray, int iArraySize);
BOOL PI_FUNC_DECL PI_TGC(int ID, const int* piTrajectoriesArray, int iArraySize);
BOOL PI_FUNC_DECL PI_TGF(int ID, const int* piTrajectoriesArray, int iArraySize);
BOOL PI_FUNC_DECL PI_TGS(int ID, const int* piTrajectoriesArray, int iArraySize);
BOOL PI_FUNC_DECL PI_qTGL(int ID, const int* piTrajectoriesArray, int* iTrajectorySizesArray, int iArraySize);
BOOL PI_FUNC_DECL PI_TGT(int ID, int iTrajectoryTiming);
BOOL PI_FUNC_DECL PI_qTGT(int ID, int* iTrajectoryTiming);

/////////////////////////////////////////////////////////////////////////////
/// Surface scan
BOOL PI_FUNC_DECL PI_FSF(int ID, const char* szAxis, double forceValue1, double positionOffset, BOOL useForceValue2, double forceValue2);
BOOL PI_FUNC_DECL PI_qFSF(int ID, const char* szAxes, double* pForceValue1Array, double* pPositionOffsetArray, double* pForceValue2Array);
BOOL PI_FUNC_DECL PI_qFSR(int ID, const char* szAxes, BOOL* pbValueArray);

/////////////////////////////////////////////////////////////////////////////
// Spezial
BOOL	PI_FUNC_DECL	PI_GetSupportedParameters(int ID, int* piParameterIdArray, int* piCommandLevelArray, int* piMemoryLocationArray, int* piDataTypeArray, int* piNumberOfItems, const int iiBufferSize, char* szParameterName, const int iMaxParameterNameSize);
BOOL	PI_FUNC_DECL	PI_GetSupportedControllers(char* szBuffer, int iBufferSize);
int		PI_FUNC_DECL	PI_GetAsyncBufferIndex(int ID);
BOOL	PI_FUNC_DECL	PI_GetAsyncBuffer(int ID, double** pdValueArray);


BOOL	PI_FUNC_DECL	PI_AddStage(int ID, const char* szAxes);
BOOL	PI_FUNC_DECL	PI_RemoveStage(int ID, const char* szStageName);
BOOL	PI_FUNC_DECL	PI_OpenUserStagesEditDialog(int ID);
BOOL	PI_FUNC_DECL	PI_OpenPiStagesEditDialog(int ID);


///////////////////////////////////////////////////////////////////////////////
// for internal use
BOOL	PI_FUNC_DECL	PI_DisableSingleStagesDatFiles(int ID,BOOL bDisable);
BOOL	PI_FUNC_DECL	PI_DisableUserStagesDatFiles(int ID,BOOL bDisable);


#ifdef __cplusplus
}
#endif
