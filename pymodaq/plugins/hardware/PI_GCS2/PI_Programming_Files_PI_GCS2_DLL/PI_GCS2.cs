/////////////////////////////////////////////////////////////////////////////
// This is a part of the PI-Software Sources
// (c)2008-2015 Physik Instrumente (PI) GmbH & Co. KG
// All rights reserved.
//

///////////////////////////////////////////////////////////////////////////// 
// Program: PI_GCS2_DLL
//
// File: PI_GCS2.cs 
/////////////////////////////////////////////////////////////////////////////

using System;
using System.Runtime.InteropServices;
using System.Text;


namespace PI
{

	/// <summary>
	/// Summary description for PI_G.
	/// </summary>
	public class GCS2
	{


        ////////////////////////////////
        // PI_GCS2 Bits (PI_BIT_XXX). //
        ////////////////////////////////

        /* Curve Controll PI_BIT_WGO_XXX */
        public const uint PI_BIT_WGO_START_DEFAULT			    = 0x00000001;
        public const uint PI_BIT_WGO_START_EXTERN_TRIGGER		= 0x00000002;
        public const uint PI_BIT_WGO_WITH_DDL_INITIALISATION	= 0x00000040;
        public const uint PI_BIT_WGO_WITH_DDL					= 0x00000080;
        public const uint PI_BIT_WGO_START_AT_ENDPOSITION		= 0x00000100;
        public const uint PI_BIT_WGO_SINGLE_RUN_DDL_TEST		= 0x00000200;
        public const uint PI_BIT_WGO_EXTERN_WAVE_GENERATOR	    = 0x00000400;
        public const uint PI_BIT_WGO_SAVE_BIT_1				    = 0x00100000;
        public const uint PI_BIT_WGO_SAVE_BIT_2				    = 0x00200000;
        public const uint PI_BIT_WGO_SAVE_BIT_3				    = 0x00400000;

        /* Wave-Trigger PI_BIT_TRG_XXX */
        public const uint PI_BIT_TRG_LINE_1					    = 0x0001;
        public const uint PI_BIT_TRG_LINE_2					    = 0x0002;
        public const uint PI_BIT_TRG_LINE_3					    = 0x0003;
        public const uint PI_BIT_TRG_LINE_4					    = 0x0008;
        public const uint PI_BIT_TRG_ALL_CURVE_POINTS			= 0x0100;

        /* Data Record Configuration PI_DRC_XXX */
        public const uint PI_DRC_DEFAULT					    = 0;
        public const uint PI_DRC_AXIS_TARGET_POS			    = 1;
        public const uint PI_DRC_AXIS_ACTUAL_POS			    = 2;
        public const uint PI_DRC_AXIS_POS_ERROR			        = 3;
        public const uint PI_DRC_AXIS_DDL_DATA			        = 4;
        public const uint PI_DRC_AXIS_DRIVING_VOL			    = 5;
        public const uint PI_DRC_PIEZO_MODEL_VOL			    = 6;
        public const uint PI_DRC_PIEZO_VOL				        = 7;
        public const uint PI_DRC_SENSOR_POS				        = 8;

        /* P(arameter)I(nfo)F(lag)_M(emory)T(ype)_XX */
        public const uint PI_PIF_MT_RAM					        = 0x00000001;
        public const uint PI_PIF_MT_EPROM					    = 0x00000002;
        public const uint PI_PIF_MT_ALL					        = (PI_PIF_MT_RAM | PI_PIF_MT_EPROM);

        /* P(arameter)I(nfo)F(lag)_D(ata)T(ype)_XX */
        public const uint PI_PIF_DT_INT					        = 1;
        public const uint PI_PIF_DT_FLOAT					    = 2;
        public const uint PI_PIF_DT_CHAR					    = 3;


        /////////////////////////////////////////////////////////////////////////////
        // DLL initialization and comm functions
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_InterfaceSetupDlg")]		    public static extern int	InterfaceSetupDlg(string sRegKeyName);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ConnectRS232")]		        public static extern int	ConnectRS232(int nPortNr, int nBaudRate);
		/**
		* Starts background thread which tries to establish connection to controller with given RS-Settings.
		* \param …
		* \return ID of new thread (>=0), error code (<0) if not
		*/        
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TryConnectRS232")]		    public static extern int	TryConnectRS232(int port, int baudrate);

		/**
		* Starts background thread which tries to establish connection to controller with given USB-Settings.
		* \param …
		* \return ID of new thread (>=0), error code (<0) if not
		*/
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TryConnectUSB")]		    	public static extern int	TryConnectUSB(string sDescription);

		/**
		* Check if thread with given ID is running trying to establish communication
		* \return TRUE if thread is running, FALSE if no thread is running with given ID
		*/
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IsConnecting")]		    	public static extern int	IsConnecting(int threadID, ref int bCOnnecting);

		/**
		* Get ID of connected controller for given threadID
		* \return ID of new controller (>=0), error code (<0) if there was an error, no thread running, or thread has not finished yet
		*/
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetControllerID")]		    public static extern int	GetControllerID(int threadID);

		/**
		* Cancel connecting thread with given ID
		* \return TRUE if thread was cancelled, FALSE if no thread with given ID was running
		*/

		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CancelConnect")]		    	public static extern int	CancelConnect(int threadID);
		
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OpenRS232DaisyChain")]		public static extern int	OpenRS232DaisyChain(int iPortNumber, int iBaudRate, ref int pNumberOfConnectedDaisyChainDevices, StringBuilder sDeviceIDNs, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ConnectDaisyChainDevice")]	public static extern int	ConnectDaisyChainDevice(int iPortId, int iDeviceNumber);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CloseDaisyChain")]		    public static extern void	CloseDaisyChain(int iPortId);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ConnectNIgpib")]		        public static extern int	ConnectNIgpib(int nBoard, int nDevAddr);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ConnectTCPIP")]		        public static extern int	ConnectTCPIP(string sHostname, int port);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_EnableTCPIPScan")]		    public static extern int	EnableTCPIPScan(int iMask);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_EnumerateTCPIPDevices")]		public static extern int	EnumerateTCPIPDevices(StringBuilder sBuffer, int iBufferSize, string sFilter);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ConnectTCPIPByDescription")]	public static extern int	ConnectTCPIPByDescription(string szDescription);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OpenTCPIPDaisyChain")]		public static extern int	OpenTCPIPDaisyChain(string sHostname, int port, ref int pNumberOfConnectedDaisyChainDevices, StringBuilder sDeviceIDNs, int iBufferSize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_EnumerateUSB")]              public static extern int    EnumerateUSB(StringBuilder sBuffer, int iBufferSize, string sFilter);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ConnectUSB")]               	public static extern int    ConnectUSB(string sDescription);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ConnectUSBWithBaudRate")]    public static extern int    ConnectUSBWithBaudRate(string sDescription, int iBaudRate);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OpenUSBDaisyChain")]         public static extern int    OpenUSBDaisyChain(string sDescription, ref int pNumberOfConnectedDaisyChainDevices, StringBuilder sDeviceIDNs, int iBufferSize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IsConnected")]		        public static extern int	IsConnected(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CloseConnection")]		    public static extern int	CloseConnection(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetError")]		            public static extern int	GetError(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SetErrorCheck")]		        public static extern int	SetErrorCheck(int ID, int bErrorCheck);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TranslateError")]		    public static extern int	TranslateError(int errNr, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SetTimeout")]                public static extern int    SetTimeout(int ID, int timeoutInMS);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SetDaisyChainScanMaxDeviceID")]	public static extern int    SetDaisyChainScanMaxDeviceID(int maxID);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_EnableReconnect")]               public static extern int    EnableReconnect(int ID, int bEnable);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SetNrTimeoutsBeforeClose")]      public static extern int    SetNrTimeoutsBeforeClose(int ID, int nrTimeoutsBeforeClose);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetInterfaceDescription")]       public static extern int    GetInterfaceDescription(int ID, StringBuilder sBuffer, int iBufferSize);



        /////////////////////////////////////////////////////////////////////////////
        // general
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qERR")]          public static extern int qERR(int ID, ref int pnError);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qIDN")]		    public static extern int qIDN(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_INI")]           public static extern int INI(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHLP")]          public static extern int qHLP(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHPA")]          public static extern int qHPA(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHPV")]          public static extern int qHPV(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCSV")]          public static extern int qCSV(int ID, ref double dCommandSyntaxVersion);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOVF")]          public static extern int qOVF(int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_RBT")]           public static extern int RBT(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_REP")]           public static extern int REP(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_BDR")]           public static extern int BDR(int ID, int iBaudRate);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qBDR")]          public static extern int qBDR(int ID, ref int iBaudRate);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DBR")]           public static extern int DBR(int ID, int iBaudRate);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDBR")]          public static extern int qDBR(int ID, ref int iBaudRate);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVER")]          public static extern int qVER(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSSN")]          public static extern int qSSN(int ID, StringBuilder sSerialNumber, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CCT")]           public static extern int CCT(int ID, int iCommandType);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCCT")]          public static extern int qCCT(int ID, ref int iCommandType);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTVI")]          public static extern int qTVI(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IFC")]           public static extern int IFC(int ID, string sParameters, string sValues);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qIFC")]          public static extern int qIFC(int ID, string sParameters, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IFS")]           public static extern int IFS(int ID, string sPassword, string sParameters, string sValues);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qIFS")]          public static extern int qIFS(int ID, string sParameters, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qECO")]          public static extern int qECO(int ID, string sSendString, StringBuilder sValues, int iBufferSize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MOV")]           public static extern int MOV(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qMOV")]          public static extern int qMOV(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MVR")]           public static extern int MVR(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MVE")]           public static extern int MVE(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_POS")]           public static extern int POS(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qPOS")]          public static extern int qPOS(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IsMoving")]      public static extern int IsMoving(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HLT")]           public static extern int HLT(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_STP")]           public static extern int STP(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qONT")]          public static extern int qONT(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_RTO")]           public static extern int RTO(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qRTO")]          public static extern int qRTO(int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ATZ")]           public static extern int ATZ(int ID, string sAxes, double[] dLowvoltageArray, int[] fUseDefaultArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qATZ")]          public static extern int qATZ(int ID, string sAxes, int[] iAtzResultArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_AOS")]          	public static extern int AOS(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qAOS")]          public static extern int qAOS(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HasPosChanged")] public static extern int HasPosChanged(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetErrorStatus")]    public static extern int GetErrorStatus(int ID, int[] bIsReferencedArray, ref int bIsReferencing, int[] bIsMovingArray, int[] bIsMotionErrorArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SVA")]           public static extern int SVA(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSVA")]          public static extern int qSVA(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_AVR")]           public static extern int SVR(int ID, string sAxes, double[] dValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DFH")]           public static extern int DFH(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDFH")]          public static extern int qDFH(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GOH")]           public static extern int GOH(int ID, string sAxes);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCST")]          public static extern int qCST(int ID, string sAxes, StringBuilder sNames, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CST")]           public static extern int CST(int ID, string sAxes, string sNames);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVST")]          public static extern int qVST(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qPUN")]          public static extern int qPUN(int ID, string sAxes, StringBuilder sUnit, int iBufferSize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_EAX")]           public static extern int PI_EAX(int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qEAX")]          public static extern int qEAX(int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SVO")]           public static extern int SVO(int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSVO")]          public static extern int qSVO(int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SMO")]           public static extern int SMO( int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSMO")]          public static extern int qSMO( int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DCO")]           public static extern int DCO(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDCO")]          public static extern int qDCO(int ID, string sAxes, int[] bValueArray);
		
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_BRA")]           public static extern int BRA(int ID, string sAxes, int[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qBRA")]          public static extern int qBRA(int ID, string sAxes, int[] iValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_RON")]           public static extern int RON(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qRON")]          public static extern int qRON(int ID, string sAxes, int[] bValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_VEL")]           public static extern int VEL(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVEL")]          public static extern int qVEL(int ID, string sAxes, double[] dValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_JOG")]      	    public static extern int JOG(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qJOG")]          public static extern int qJOG(int ID, string sAxes, double[] dValueArray);
		
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTCV")]          public static extern int qTCV(int ID, string sAxes, double[] dValueArray);

		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_VLS")]           public static extern int VLS(int ID, double dSystemVelocity);
		[DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVLS")]          public static extern int qVLS(int ID, ref double dSystemVelocity);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ACC")]           public static extern int ACC(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qACC")]          public static extern int qACC(int ID, string sAxes, double[] dValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DEC")]           public static extern int DEC(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDEC")]          public static extern int qDEC(int ID, string sAxes, double[] dValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_VCO")]           public static extern int VCO(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVCO")]          public static extern int qVCO(int ID, string sAxes, int[] bValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SPA")]           public static extern int SPA(int ID, string sAxes, uint[] iParameterArray, double[] dValueArray, string sStrings);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSPA")]          public static extern int qSPA(int ID, string sAxes, uint[] iParameterArray, double[] dValueArray, StringBuilder sStrings, int iMaxNameSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SEP")]           public static extern int SEP(int ID, string sPassword, string sAxes, uint[] iParameterArray, double[] dValueArray, string sStrings);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSEP")]          public static extern int qSEP(int ID, string sAxes, uint[] iParameterArray, double[] dValueArray, StringBuilder sStrings, int iMaxNameSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WPA")]           public static extern int WPA(int ID, string sPassword, string sAxes, uint[] iParameterArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DPA")]           public static extern int DPA(int ID, string sPassword, string sAxes, uint[] iParameterArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TIM")]           public static extern int TIM(int ID, double dTimer);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTIM")]          public static extern int qTIM(int ID, ref double dTimer);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_RPA")]           public static extern int RPA(int ID, string sAxes, int uiParameterArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SPA_String")]    public static extern int SPA_String(int ID, string sAxes, uint[] iParameterArray, string sStrings);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSPA_String")]   public static extern int qSPA_String(int ID, string sAxes, uint[] iParameterArray, StringBuilder sStrings, int iMaxNameSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SEP_String")]    public static extern int SEP_String(int ID, string sPassword, string sAxes, uint[] iParameterArray, string sStrings);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSEP_String")]   public static extern int qSEP_String(int ID, string sAxes, uint[] iParameterArray, StringBuilder sStrings, int iMaxNameSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SPA_int64")] 	public static extern int SPA_int64(int ID, string sAxes, uint[] iParameterArray, long[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSPA_int64")]   	public static extern int qSPA_int64(int ID, string sAxes, uint[] iParameterArray, long[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SEP_int64")]   	public static extern int SEP_int64(int ID, string sPassword, string sAxes, uint[] iParameterArray, long[] iValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSEP_int64")]   	public static extern int qSEP_int64(int ID, string sAxes, uint[] iParameterArray, long[] iValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_STE")]            public static extern int STE(int ID, string sAxes, double[] dOffsetArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSTE")]           public static extern int qSTE(int ID, string sAxes, double[] pdValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IMP")]            public static extern int IMP(int ID, string sAxes, double[] dImpulseSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IMP_PulseWidth")] public static extern int IMP_PulseWidth(int ID, char cAxis, double dOffset, int iPulseWidth);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qIMP")]           public static extern int qIMP(int ID, string sAxes, double[] dValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SAI")]           public static extern int SAI(int ID, string sOldAxes, string sNewAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSAI")]          public static extern int qSAI(int ID, StringBuilder sAxes, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSAI_ALL")]      public static extern int qSAI_ALL(int ID, StringBuilder sAxes, int iBufferSize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CCL")]           public static extern int CCL(int ID, int iComandLevel, string sPassWord);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCCL")]          public static extern int qCCL(int ID, ref int iComandLevel);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_AVG")]           public static extern int AVG(int ID, int iAverrageTime);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qAVG")]          public static extern int qAVG(int ID, ref int iAverrageTime);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHAR")]          public static extern int qHAR(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qLIM")]          public static extern int qLIM(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTRS")]          public static extern int qTRS(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FNL")]           public static extern int FNL(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFPH")]          public static extern int qFPH(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FPH")]           public static extern int FPH(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FPL")]           public static extern int FPL(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FRF")]           public static extern int FRF(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FED")]           public static extern int FED(int ID, string sAxes, int[] iEdgeArray, int[] piParamArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFRF")]          public static extern int qFRF(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DIO")]           public static extern int DIO(int ID, int[] iChannelsArray, int[] bValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDIO")]          public static extern int qDIO(int ID, int[] iChannelsArray, int[] bValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTIO")]          public static extern int qTIO(int ID, ref int iInputNr, ref int iOutputNr);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IsControllerReady")] public static extern int IsControllerReady(int ID, ref int iControllerReady);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSRG")]          public static extern int qSRG(int ID, string sAxes, int[] iRegisterArray, int[] iValArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ATC")]           public static extern int ATC(int ID, int[] iChannels, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qATC")]          public static extern int qATC(int ID, int[] iChannels, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qATS")]          public static extern int qATS(int ID, int[] iChannels, int[] iOptions, int[] iValueArray, int iArraySize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SPI")]           public static extern int SPI(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSPI")]          public static extern int qSPI(int ID, string sAxes, double[] dValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SCT")]           public static extern int SCT(int ID, double dCycleTime);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSCT")]          public static extern int qSCT(int ID, ref double pdCycleTime);
		
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SST")]           public static extern int SST(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSST")]          public static extern int qSST(int ID, string sAxes, double[] dValueArray);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCTV")]          public static extern int qCTV(int ID, string sAxes, double[] dValarray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CTV")]           public static extern int CTV(int ID, string sAxes, double[] dValarray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CTR")]           public static extern int CTR(int ID, string sAxes, double[] dValarray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCAV")]          public static extern int qCAV(int ID, string sAxes, double[] dValarray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCCV")]          public static extern int qCCV(int ID, string sAxes, double[] dValarray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCMO")]          public static extern int qCMO(int ID, string sAxes, int[] iValArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CMO")]           public static extern int CMO(int ID, string sAxes, int[] iValArray);
        
        
        /////////////////////////////////////////////////////////////////////////////
        // Macro commande
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IsRunningMacro")] public static extern int IsRunningMacro(int ID, int[] bRunningMacro);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_BEG")]       public static extern int MAC_BEG(int ID, string sMacroName);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_START")]     public static extern int MAC_START(int ID, string sMacroName);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_NSTART")]    public static extern int MAC_NSTART(int ID, string sMacroName, int nrRuns);
		
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_START_Args")]	public static extern int MAC_START_Args(int ID, string sMacroName, string[] sArgs);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_NSTART_Args")]   public static extern int MAC_NSTART_Args(int ID, string sMacroName, int nrRuns, string sArgs);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_END")]       public static extern int MAC_END(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_DEL")]       public static extern int MAC_DEL(int ID, string sMacroName);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_DEF")]       public static extern int MAC_DEF(int ID, string sMacroName);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_qDEF")]      public static extern int MAC_qDEF(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_qERR")]      public static extern int MAC_qERR(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MAC_qFRE")]      public static extern int MAC_qFREE(int ID, ref int iFreeSpace);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qMAC")]          public static extern int qMAC(int ID, string sMacroName, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qRMC")]          public static extern int qRMC(int ID, StringBuilder sBuffer, int iBufferSize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DEL")]           public static extern int DEL(int ID, int nMilliSeconds);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WAC")]           public static extern int WAC(int ID, string sCondition);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MEX")]           public static extern int MEX(int ID, string sCondition);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_VAR")]           public static extern int VAR(int ID, string sVariable, string sValue);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVAR")]          public static extern int qVAR(int ID, string sVariables, StringBuilder sValues,  int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ADD")]           public static extern int ADD(int ID, string sVariable, double value1, double value2);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CPY")]           public static extern int CPY(int ID, string sVariable, string sCommand);


        /////////////////////////////////////////////////////////////////////////////
        // String commands.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GcsCommandset")]    public static extern int GcsCommandset(int ID, string sCommand);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GcsGetAnswer")]     public static extern int GcsGetAnswer(int ID, StringBuilder sAnswer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GcsGetAnswerSize")] public static extern int GcsGetAnswerSize(int ID, ref int iAnswerSize);


        /////////////////////////////////////////////////////////////////////////////
        // limits.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTMN")]          public static extern int qTMN(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTMX")]          public static extern int qTMX(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_NLM")]           public static extern int NLM(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qNLM")]          public static extern int qNLM(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_PLM")]           public static extern int PLM(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qPLM")]          public static extern int qPLM(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SSL")]           public static extern int SSL(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSSL")]          public static extern int qSSL(int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVMO")]          public static extern int qVMO(int ID, string sAxes, double[] dValarray, int[] bMovePossible);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCMN")]          public static extern int qCMN(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCMX")]          public static extern int qCMX(int ID, string sAxes, double[] dValueArray);


        /////////////////////////////////////////////////////////////////////////////
        // Wave commands.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_IsGeneratorRunning")] public static extern int IsGeneratorRunning(int ID, int[] iWaveGeneratorIds, int[] bValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTWG")]          public static extern int qTWG(int ID, ref int iWaveGenerators);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WAV_SIN_P")]     public static extern int WAV_SIN_P(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iCenterPointOfWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WAV_LIN")]       public static extern int WAV_LIN(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iNumberOfSpeedUpDownPointsInWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WAV_NOISE")]     public static extern int WAV_NOISE(int ID, int iWaveTableId, int iAddAppendWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);   
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WAV_RAMP")]      public static extern int WAV_RAMP(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, int iCenterPointOfWave, int iNumberOfSpeedUpDownPointsInWave, double dAmplitudeOfWave, double dOffsetOfWave, int iSegmentLength);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WAV_PNT")]       public static extern int WAV_PNT(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfPoints, int iAddAppendWave, double[] dWavePoints);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWAV")]          public static extern int qWAV(int ID, int[] iWaveTableIdsArray, int[] iParamereIdsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WGO")]           public static extern int WGO(int ID, int[] iWaveGeneratorIdsArray, int[] iStartModArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWGO")]          public static extern int qWGO(int ID, int[] iWaveGeneratorIdsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WGC")]           public static extern int WGC(int ID, int[] iWaveGeneratorIdsArray, int[] iNumberOfCyclesArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWGC")]          public static extern int qWGC(int ID, int[] iWaveGeneratorIdsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWGI")]          public static extern int qWGI(int ID, int[] iWaveGeneratorIdsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWGN")]          public static extern int qWGN(int ID, int[] iWaveGeneratorIdsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WSL")]           public static extern int WSL(int ID, int[] iWaveGeneratorIdsArray, int[] iWaveTableIdsArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWSL")]          public static extern int qWSL(int ID, int[] iWaveGeneratorIdsArray, int[] iWaveTableIdsArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DTC")]           public static extern int DTC(int ID, int[] iDdlTableIdsArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDTL")]          public static extern int qDTL(int ID, int[] iDdlTableIdsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WCL")]           public static extern int WCL(int ID, int[] iWaveTableIdsArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTLT")]          public static extern int qTLT(int ID, int[] iNumberOfDdlTables);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qGWD_SYNC")]     public static extern int qGWD_SYNC(int ID, int iWaveTableId, int iOffsetOfFirstPointInWaveTable, int iNumberOfValues, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qGWD")]          public static extern int qGWD(int ID, int[] iWaveTableIdsArray, int iNumberOfWaveTables, int iOffset, int nrValues, ref IntPtr dValarray, StringBuilder sGcsArrayHeader, int iGcsArrayHeaderMaxSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WOS")]           public static extern int WOS(int ID, int[] iWaveTableIdsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWOS")]          public static extern int qWOS(int ID, int[] iWaveTableIdsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WTR")]           public static extern int WTR(int ID, int[] iWaveGeneratorIdsArray, int[] iTableRateArray, int[] iInterpolationTypeArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWTR")]          public static extern int qWTR(int ID, int[] iWaveGeneratorIdsArray, int[] iTableRateArray, int[] iInterpolationTypeArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DDL")]           public static extern int DDL(int ID, int iDdlTableId,  int iOffsetOfFirstPointInDdlTable,  int iNumberOfValues, double[] pdValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDDL_SYNC")]     public static extern int qDDL_SYNC(int ID,  int iDdlTableId,  int iOffsetOfFirstPointInDdlTable,  int iNumberOfValues, double[] pdValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDDL")]          public static extern int qDDL(int ID, int[] iDdlTableIdsArray, int iNumberOfDdlTables, int iOffset, int nrValues, ref IntPtr  dValarray, StringBuilder szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DPO")]           public static extern int DPO(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qWMS")]          public static extern int qWMS(int ID, int[] iWaveTableIds, int[] iWaveTableMaimumSize, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TWE")]           public static extern int TWE(int ID, int[] iWaveTableIdsArray, int[] iWaveTableStartIndexArray, int[] iWaveTableEndIndexArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTEW")]          public static extern int qTWE(int ID, int[] iWaveTableIdsArray, int[] iWaveTableStartIndexArray, int[] iWaveTableEndIndexArray, int iArraySize);



        /////////////////////////////////////////////////////////////////////////////
        // Trigger commands.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TWC")]           public static extern int TWC(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TWS")]           public static extern int TWS(int ID, int[] iTriggerChannelIdsArray, int[] piPointNumberArray, int[] piSwitchArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTWS")]          public static extern int qTWS(int ID, int[] iTriggerChannelIdsArray, int iNumberOfTriggerChannels, int iOffset, int nrValues, ref IntPtr dValarray, StringBuilder szGcsArrayHeader, int iGcsArrayHeaderMaxSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CTO")]           public static extern int CTO(int ID, int[] iTriggerOutputIdsArray, int[] iTriggerParameterArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CTOString")]     public static extern int CTOString(int ID, int[] iTriggerOutputIds, int[] iTriggerParameterArray, string sValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCTO")]          public static extern int qCTO(int ID, int[] iTriggerOutputIdsArray, int[] iTriggerParameterArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCTOString")]    public static extern int qCTOString(int ID, int[] piTriggerOutputIds, int[] piTriggerParameterArray, StringBuilder sValueArray, int iArraySize, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TRO")]           public static extern int TRO(int ID, long[] iTriggerChannelIds, int[] bTriggerChannelEnabel, long iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTRO")]          public static extern int qTRO(int ID, long[] iTriggerChannelIds, int[] bTriggerChannelEnabel, long iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_TRI")]           public static extern int TRI(int ID, int[] iTriggerInputIds, int[] bTriggerState, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTRI")]          public static extern int qTRI(int ID, int[] iTriggerInputIds, int[] bTriggerState, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_CTI")]           public static extern int CTI(int ID, int[] iTriggerInputIds, int[] iTriggerParameterArray, string sValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCTI")]          public static extern int qCTI(int ID,  int[] iTriggerInputIds, int[] iTriggerParameterArray, StringBuilder sValueArray, int iArraySize, int iBufferSize);


        /////////////////////////////////////////////////////////////////////////////
        // Record tabel commands.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHDR")]          public static extern int qHDR(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTNR")]          public static extern int qTNR(int ID, ref int iNumberOfRecordCannels);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DRC")]           public static extern int DRC(int ID, int[] iRecordTableIdsArray, string sRecordSourceIds, int[] iRecordOptionArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDRC")]          public static extern int qDRC(int ID, int[] iRecordTableIdsArray, StringBuilder szRecordSourceIds, int[] iRecordOptionArray, int iRecordSourceIdsBufferSize, int iRecordOptionArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDRR_SYNC")]     public static extern int qDRR_SYNC(int ID,  int iRecordTablelId,  int iOffsetOfFirstPointInRecordTable,  int iNumberOfValues, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDRR")]          public static extern int qDRR(int ID, int[] iRecTableIdsArray, int iNumberOfRecChannels, int iOffsetOfFirstPointInRecordTable, int iNumberOfValues, ref IntPtr dValueArray, StringBuilder sGcsArrayHeader, int iGcsArrayHeaderMaxSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_DRT")]           public static extern int DRT(int ID, int[] iRecordChannelIdsArray, int[] iTriggerSourceArray, string sValues, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDRT")]          public static extern int qDRT(int ID, int[] iRecordChannelIdsArray, int[] iTriggerSourceArray, StringBuilder sValues, int iArraySize, int iValueBufferLength);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_RTR")]           public static extern int RTR(int ID, int iReportTableRate);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qRTR")]          public static extern int qRTR(int ID, ref int iReportTableRate);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_WGR")]           public static extern int WGR(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDRL")]          public static extern int qDRL(int ID, int[] iRecordChannelIdsArray, int[] iNuberOfRecordedValuesArray, int iArraySize);


        /////////////////////////////////////////////////////////////////////////////
        // Piezo-Channel commands.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_VMA")]           public static extern int VMA(int ID, int[] iPiezoChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVMA")]          public static extern int qVMA(int ID, int[] iPiezoChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_VMI")]           public static extern int VMI(int ID, int[] iPiezoChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVMI")]          public static extern int qVMI(int ID, int[] iPiezoChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_VOL")]           public static extern int VOL(int ID, int[] iPiezoChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qVOL")]          public static extern int qVOL(int ID, int[] iPiezoChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTPC")]          public static extern int qTPC(int ID, ref int iNumberOfPiezoChannels);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ONL")]           public static extern int ONL(int ID, int[] iPiezoChannelsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qONL")]          public static extern int qONL(int ID, int[] iPiezoChannelsArray, int[] iValueArray, int iArraySize);


        /////////////////////////////////////////////////////////////////////////////
        // Sensor-Channel commands.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTAD")]          public static extern int qTAD(int ID, int[] iSensorsChannelsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTNS")]          public static extern int qTNS(int ID, int[] iSensorsChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTSP")]          public static extern int qTSP(int ID, int[] iSensorsChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SCN")]           public static extern int SCN(int ID, int[] iSensorsChannelsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSCN")]          public static extern int qSCN(int ID, int[] iSensorsChannelsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTSC")]          public static extern int qTSC(int ID, ref int iNumberOfSensorChannels);


        /////////////////////////////////////////////////////////////////////////////
        // PIEZOWALK(R)-Channel commands.
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_APG")]           public static extern int APG(int ID, int[] iPIEZOWALKChannelsArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSPG")]          public static extern int qAPG(int ID, int[] iPIEZOWALKChannelsArray, int[] iValueArray, int iArraySize);
		
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OAC")]           public static extern int OAC(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOAC")]          public static extern int qOAC(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OAD")]           public static extern int OAD(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOAD")]          public static extern int qOAD(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_ODC")]           public static extern int ODC(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qODC")]          public static extern int qODC(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OCD")]           public static extern int OCD(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOCD")]          public static extern int qOCD(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OSM")]           public static extern int OSM(int ID, int[] iPIEZOWALKChannelsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOSM")]          public static extern int qOSM(int ID, int[] iPIEZOWALKChannelsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOSMf")]         public static extern int OSMf(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOSMf")]         public static extern int qOSMf(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OVL")]           public static extern int OVL(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOVL")]          public static extern int qOVL(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOSN")]          public static extern int qOSN(int ID, int[] iPIEZOWALKChannelsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SSA")]           public static extern int SSA(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSSA")]          public static extern int qSSA(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_RNP")]           public static extern int RNP(int ID, int[] iPIEZOWALKChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_PGS")]           public static extern int PGS(int ID, int[] iPIEZOWALKChannelsArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTAC")]          public static extern int qTAC(int ID, ref int nNrChannels);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTAV")]          public static extern int qTAV(int ID, int[] iChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OMA")]           public static extern int OMA(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qOMA")]          public static extern int qOMA(int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OMR")]           public static extern int OMR(int ID, string sAxes, double[] dValueArray);


        /////////////////////////////////////////////////////////////////////////////
        // Joystick
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qJAS")]          public static extern int qJAS(int ID, int[] iJoystickIDsArray, int[] iAxesIDsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_JAX")]           public static extern int JAX(int ID,  int iJoystickID,  int iAxesID, string sAxesBuffer);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qJAX")]          public static extern int qJAX(int ID, int[] iJoystickIDsArray, int[] iAxesIDsArray, int iArraySize, StringBuilder sAxesBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qJBS")]          public static extern int qJBS(int ID, int[] iJoystickIDsArray, int[] iButtonIDsArray, int[] bValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_JDT")]           public static extern int JDT(int ID, int[] iJoystickIDsArray, int[] iAxisIDsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_JLT")]           public static extern int JLT(int ID, int iJoystickID, int iAxisID, int iStartAdress, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qJLT")]          public static extern int qJLT(int ID, int[] iJoystickIDsArray, int[] iAxisIDsArray,  int iNumberOfTables,  int iOffsetOfFirstPointInTable, int iNumberOfValues, ref IntPtr dValueArray, StringBuilder sGcsArrayHeader, int iGcsArrayHeaderMaxSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_JON")]           public static extern int JON(int ID, int[] iJoystickIDsArray, int[] bValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qJON")]          public static extern int qJON(int ID, int[] iJoystickIDsArray, int[] bValueArray, int iArraySize);


		/////////////////////////////////////////////////////////////////////////////
		// fast scan commands
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_AAP")]           public static extern int AAP(int ID, char[] sAxis1, double dLength1, char[] sAxis2, double dLength2, double dAlignStep, int iNrRepeatedPositions, int iAnalogInput);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FIO")]           public static extern int FIO(int ID, char[] sAxis1, double dLength1, char[] sAxis2, double dLength2, double dThreshold, double dLinearStep, double dAngleScan, int iAnalogInput);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FLM")]           public static extern int FLM(int ID, char[] sAxis, double dLength, double dThreshold, int iAnalogInput, int iDirection);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FLS")]           public static extern int FLS(int ID, char[] sAxis, double dLength, double dThreshold, int iAnalogInput, int iDirection);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FSA")]           public static extern int FSA(int ID, char[] sAxis1, double dLength1, char[] sAxis2, double dLength2, double dThreshold, double dDistance, double dAlignStep, int iAnalogInput);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FSC")]           public static extern int FSC(int ID, char[] sAxis1, double dLength1, char[] sAxis2, double dLength2, double dThreshold, double dDistance, int iAnalogInput);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FSM")]           public static extern int FSM(int ID, char[] sAxis1, double dLength1, char[]  sAxis2, double dLength2, double dThreshold, double dDistance, int iAnalogInput);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFSS")]          public static extern int qFSS(int ID, ref int piResult);


		/////////////////////////////////////////////////////////////////////////////
		// optical boards (hexapod)
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SGA")]           public static extern int SGA(int ID, int[] iAnalogChannelIds, int[] iGainValues, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSGA")]          public static extern int qSGA(int ID, int[] iAnalogChannelIds, int[] iGainValues, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_NAV")]           public static extern int NAV(int ID, int[] iAnalogChannelIds, int[] iNrReadingsValues, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qNAV")]          public static extern int qNAV(int ID, int[] iAnalogChannelIds, int[] iNrReadinPI_FNLgsValues, int iArraySize);
		// more hexapod specific
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetDynamicMoveBufferSize")]	public static extern int GetDynamicMoveBufferSize(int ID, ref int iSize);

		
		/////////////////////////////////////////////////////////////////////////////
		// PIShift
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qCOV")]          public static extern int qCOV(int ID, int[] iChannelsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MOD")]           public static extern int MOD(int ID, string sItems, uint[] iModeArray, string sValues);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qMOD")]          public static extern int qMOD(int ID, string sItems, uint[] iModeArray, StringBuilder sValues, int iMaxValuesSize);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qDIA")]          public static extern int qDIA(int ID, uint[] iIDArray, StringBuilder sValues,  int iBufferSize, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHDI")]          public static extern int qHDI(int ID, StringBuilder sBuffer,  int iBufferSize);

		
		/////////////////////////////////////////////////////////////////////////////
		// HID
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHIS")]          public static extern int qHIS (int ID, StringBuilder sBuffer,  int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HIS")]           public static extern int HIS  (int ID, int[]iDeviceIDsArray, int[] iItemIDsArray, int[] iPropertyIDArray, string sValues, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHIE")]          public static extern int qHIE (int ID, int[] iDeviceIDsArray, int[] iAxesIDsArray, double[] dValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHIB")]          public static extern int qHIB (int ID, int[] iDeviceIDsArray, int[] iButtonIDsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HIL")]           public static extern int HIL  (int ID, int[] iDeviceIDsArray, int[] iLED_IDsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHIL")]          public static extern int qHIL (int ID, int[] iDeviceIDsArray, int[] iLED_IDsArray, int[] iValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HIN")]           public static extern int HIN  (int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHIN")]          public static extern int qHIN (int ID, string sAxes, int[] bValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HIA")]           public static extern int HIA  (int ID, string sAxes, int[] iFunctionArray, int[] iDeviceIDsArray, int[] iAxesIDsArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHIA")]          public static extern int qHIA (int ID, string sAxes, int[] iFunctionArray, int[] iDeviceIDsArray, int[] iAxesIDsArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HDT")]           public static extern int HDT  (int ID, int[] iDeviceIDsArray, int[] iAxisIDsArray, int[] piValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHDT")]          public static extern int qHDT (int ID, int[] iDeviceIDsArray, int[] iAxisIDsArray, int[] piValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_HIT")]           public static extern int HIT  (int ID, int[] iTableIdsArray, int[] iPointNumberArray, double[] pdValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qHIT")]          public static extern int qHIT (int ID, int[] iTableIdsArray,  int iNumberOfTables,  int iOffsetOfFirstPointInTable,  int iNumberOfValues, ref IntPtr pdValueArray, StringBuilder sGcsArrayHeader, int iGcsArrayHeaderMaxSize);

		
		/////////////////////////////////////////////////////////////////////////////
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qMAN")]          public static extern int qMAN(int ID, String sCommand, StringBuilder sBuffer,  int iBufferSize);

		
		/////////////////////////////////////////////////////////////////////////////
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KSF")]           public static extern int KSF  (int ID, string sNameOfCoordSystem);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KEN")]           public static extern int KEN  (int ID, string sNameOfCoordSystem);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KRM")]           public static extern int KRM  (int ID, string sNameOfCoordSystem);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KLF")]           public static extern int KLF  (int ID, string sNameOfCoordSystem);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KSD")]           public static extern int KSD  (int ID, string sNameOfCoordSystem, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KST")]           public static extern int KST  (int ID, string sNameOfCoordSystem, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KSW")]           public static extern int KSW  (int ID, string sNameOfCoordSystem, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KLD")]           public static extern int KLD  (int ID, string sNameOfCoordSystem, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KSB")]           public static extern int KSB  (int ID, string sNameOfCoordSystem, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MRT")]           public static extern int MRT  (int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_MRW")]           public static extern int MRW  (int ID, string sAxes, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qKLT")]          public static extern int qKLT (int ID, string sStartCoordSystem, string sEndCoordSystem, StringBuilder buffer, int bufsize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qKEN")]          public static extern int qKEN (int ID, string sNamesOfCoordSystems, StringBuilder buffer, int bufsize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qKET")]          public static extern int qKET (int ID, string sTypes, StringBuilder buffer, int bufsize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qKLS")]          public static extern int qKLS (int ID, string sNameOfCoordSystem, string sItem1, string sItem2, StringBuilder buffer, int bufsize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KLN")]           public static extern int KLN  (int ID, string sNameOfChild, string sNameOfParent);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qKLN")]          public static extern int qKLN (int ID, string sNamesOfCoordSystems, StringBuilder buffer, int bufsize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTRA")]          public static extern int qTRA (int ID, string sAxes, double[] dComponents, double[] dValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qKLC")]          public static extern int qKLC (int ID, string sNameOfCoordSystem1, string sNameOfCoordSystem2, string sItem1, string sItem2, StringBuilder buffer, int bufsize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_KCP")]           public static extern int KCP  (int ID, string sSource, string sDestination);



        /////////////////////////////////////////////////////////////////////////////
        // Spezial
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetSupportedFunctions")]     public static extern int GetSupportedFunctions(int ID, int[] iComandLevelArray, int iBufferSize, StringBuilder sFunctionNames, int iMaxFunctioNamesLength);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetSupportedParameters")]    public static extern int GetSupportedParameters(int ID, int[] iParameterIdArray, int[] iComandLevelArray, int[] iMennoryLocationArray, int[] iDataTypeArray, int[] iNumberOfItems, int iBufferSize, StringBuilder sParameterName, int iMaxParameterNameSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetSupportedControllers")]   public static extern int GetSupportedControllers(StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetAsyncBufferIndex")]       public static extern int GetAsyncBufferIndex(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_GetAsyncBuffer")]            public static extern int GetAsyncBuffer(int ID, ref IntPtr pdValueArray);


        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_AddStage")]                  public static extern int AddStage(int ID, string sAxes);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_RemoveStage")]               public static extern int RemoveStage(int ID, string sStageName);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OpenUserStagesEditDialog")]  public static extern int OpenUserStagesEditDialog(int ID);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_OpenPiStagesEditDialog")]    public static extern int OpenPiStagesEditDialog(int ID);

        /////////////////////////////////////////////////////////////////////////////
        // Fast Alignment
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FDG")]                       public static extern int FDG(int ID, string szScanRoutineName, string szScanAxis, string szStepAxis, string szParameters);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FDR")]                       public static extern int FDR(int ID, string szScanRoutineName, string szScanAxis, double dScanAxisRange, string szStepAxis, double dStepAxisRange, string szParameters);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FGC")]                       public static extern int FGC(int ID, string szProcessIds, double[] pdScanAxisCenterValueArray, double[] pdStepAxisCenterValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFGC")]                      public static extern int qFGC(int ID, string szProcessIds, double[] pdScanAxisCenterValueArray, double[] pdStepAxisCenterValueArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FRC")]                       public static extern int FRC(int ID, string szProcessIdBase, string szProcessIdsCouplet);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFRC")]                      public static extern int qFRC(int ID, string szProcessIdsBase, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFRH")]                      public static extern int qFRH(int ID, StringBuilder sBuffer, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FRP")]                       public static extern int FRP(int ID, string szScanRoutineNames,  int[] piOptionsArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFRP")]                      public static extern int qFRP(int ID, string szScanRoutineNames, int[] piOptionsArray);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qFRR")]                      public static extern int qFRR(int ID, string szScanRoutineNames, int iResultId, StringBuilder sResult, int iBufferSize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_FRS")]                       public static extern int FRS(int ID, string szScanRoutineNames);

        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qTCI")]                      public static extern int qTCI(int ID, int[] piFastAlignmentInputIdsArray, double[] pdCalculatedInputValueArray, int iArraySize);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_SIC")]                       public static extern int SIC(int ID, int iFastAlignmentInputId, int iCalcType, double[] pdParameters, int iNumberOfParameters);
        [DllImport("PI_GCS2_DLL.dll", EntryPoint = "PI_qSIC")]                      public static extern int qSIC(int ID, int[] piFastAlignmentInputIdsArray, int iNumberOfInputIds, StringBuilder sBuffer, int iBufferSize);
    }
}
