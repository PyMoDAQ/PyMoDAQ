from PyQt5.QtCore import QThread
import numpy as np
import pymodaq.daq_utils.daq_utils as mylib
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
from easydict import EasyDict as edict
from collections import OrderedDict
from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_viewer.utility_classes import comon_parameters

from enum import IntEnum
import cv2


class OpenCVProp(IntEnum):
    # modes of the controlling registers (can be: auto, manual, auto single push, absolute Latter allowed with any other mode)
    # every feature can have only one mode turned on at a time
    CV_CAP_PROP_DC1394_OFF         = -4,  #turn the feature off (not controlled manually nor automatically)
    CV_CAP_PROP_DC1394_MODE_MANUAL = -3, #set automatically when a value of the feature is set by the user
    CV_CAP_PROP_DC1394_MODE_AUTO = -2,
    CV_CAP_PROP_DC1394_MODE_ONE_PUSH_AUTO = -1;
    CV_CAP_PROP_POS_MSEC       =0;
    CV_CAP_PROP_POS_FRAMES     =1;
    CV_CAP_PROP_POS_AVI_RATIO  =2;
    CV_CAP_PROP_FRAME_WIDTH    =3;
    CV_CAP_PROP_FRAME_HEIGHT   =4;
    CV_CAP_PROP_FPS            =5;
    CV_CAP_PROP_FOURCC         =6;
    CV_CAP_PROP_FRAME_COUNT    =7;
    CV_CAP_PROP_FORMAT         =8;
    CV_CAP_PROP_MODE           =9;
    CV_CAP_PROP_BRIGHTNESS    =10;
    CV_CAP_PROP_CONTRAST      =11;
    CV_CAP_PROP_SATURATION    =12;
    CV_CAP_PROP_HUE           =13;
    CV_CAP_PROP_GAIN          =14;
    CV_CAP_PROP_EXPOSURE      =15;
    CV_CAP_PROP_CONVERT_RGB   =16;
    CV_CAP_PROP_WHITE_BALANCE_BLUE_U =17;
    CV_CAP_PROP_RECTIFICATION =18;
    CV_CAP_PROP_MONOCHROME    =19;
    CV_CAP_PROP_SHARPNESS     =20;
    CV_CAP_PROP_AUTO_EXPOSURE =21; # exposure control done by camera;
                                   # user can adjust reference level
                                   # using this feature
    CV_CAP_PROP_GAMMA         =22;
    CV_CAP_PROP_TEMPERATURE   =23;
    CV_CAP_PROP_TRIGGER       =24;
    CV_CAP_PROP_TRIGGER_DELAY =25;
    CV_CAP_PROP_WHITE_BALANCE_RED_V =26;
    CV_CAP_PROP_ZOOM          =27;
    CV_CAP_PROP_FOCUS         =28;
    CV_CAP_PROP_GUID          =29;
    CV_CAP_PROP_ISO_SPEED     =30;
    CV_CAP_PROP_MAX_DC1394    =31;
    CV_CAP_PROP_BACKLIGHT     =32;
    CV_CAP_PROP_PAN           =33;
    CV_CAP_PROP_TILT          =34;
    CV_CAP_PROP_ROLL          =35;
    CV_CAP_PROP_IRIS          =36;
    CV_CAP_PROP_SETTINGS      =37;
    CV_CAP_PROP_BUFFERSIZE    =38;
    CV_CAP_PROP_AUTOFOCUS     =39;
    CV_CAP_PROP_SAR_NUM       =40;
    CV_CAP_PROP_SAR_DEN       =41;

    CV_CAP_PROP_AUTOGRAB      =1024; # property for videoio class CvCapture_Android only
    CV_CAP_PROP_SUPPORTED_PREVIEW_SIZES_STRING=1025; # readonly; tricky property; returns cpnst char* indeed
    CV_CAP_PROP_PREVIEW_FORMAT=1026; # readonly; tricky property; returns cpnst char* indeed

    # OpenNI map generators
    CV_CAP_OPENNI_DEPTH_GENERATOR = 1 << 31;
    CV_CAP_OPENNI_IMAGE_GENERATOR = 1 << 30;
    CV_CAP_OPENNI_IR_GENERATOR    = 1 << 29;
    CV_CAP_OPENNI_GENERATORS_MASK = CV_CAP_OPENNI_DEPTH_GENERATOR + CV_CAP_OPENNI_IMAGE_GENERATOR + CV_CAP_OPENNI_IR_GENERATOR;

    # Properties of cameras available through OpenNI interfaces
    CV_CAP_PROP_OPENNI_OUTPUT_MODE     = 100;
    CV_CAP_PROP_OPENNI_FRAME_MAX_DEPTH = 101; # in mm
    CV_CAP_PROP_OPENNI_BASELINE        = 102; # in mm
    CV_CAP_PROP_OPENNI_FOCAL_LENGTH    = 103; # in pixels
    CV_CAP_PROP_OPENNI_REGISTRATION    = 104; # flag
    CV_CAP_PROP_OPENNI_REGISTRATION_ON = CV_CAP_PROP_OPENNI_REGISTRATION; # flag that synchronizes the remapping depth map to image map
                                                                          # by changing depth generator's view point (if the flag is "on") or
                                                                          # sets this view point to its normal one (if the flag is "off").
    CV_CAP_PROP_OPENNI_APPROX_FRAME_SYNC = 105;
    CV_CAP_PROP_OPENNI_MAX_BUFFER_SIZE   = 106;
    CV_CAP_PROP_OPENNI_CIRCLE_BUFFER     = 107;
    CV_CAP_PROP_OPENNI_MAX_TIME_DURATION = 108;

    CV_CAP_PROP_OPENNI_GENERATOR_PRESENT = 109;
    CV_CAP_PROP_OPENNI2_SYNC = 110;
    CV_CAP_PROP_OPENNI2_MIRROR = 111;

    CV_CAP_OPENNI_IMAGE_GENERATOR_PRESENT         = CV_CAP_OPENNI_IMAGE_GENERATOR + CV_CAP_PROP_OPENNI_GENERATOR_PRESENT;
    CV_CAP_OPENNI_IMAGE_GENERATOR_OUTPUT_MODE     = CV_CAP_OPENNI_IMAGE_GENERATOR + CV_CAP_PROP_OPENNI_OUTPUT_MODE;
    CV_CAP_OPENNI_DEPTH_GENERATOR_PRESENT         = CV_CAP_OPENNI_DEPTH_GENERATOR + CV_CAP_PROP_OPENNI_GENERATOR_PRESENT;
    CV_CAP_OPENNI_DEPTH_GENERATOR_BASELINE        = CV_CAP_OPENNI_DEPTH_GENERATOR + CV_CAP_PROP_OPENNI_BASELINE;
    CV_CAP_OPENNI_DEPTH_GENERATOR_FOCAL_LENGTH    = CV_CAP_OPENNI_DEPTH_GENERATOR + CV_CAP_PROP_OPENNI_FOCAL_LENGTH;
    CV_CAP_OPENNI_DEPTH_GENERATOR_REGISTRATION    = CV_CAP_OPENNI_DEPTH_GENERATOR + CV_CAP_PROP_OPENNI_REGISTRATION;
    CV_CAP_OPENNI_DEPTH_GENERATOR_REGISTRATION_ON = CV_CAP_OPENNI_DEPTH_GENERATOR_REGISTRATION;
    CV_CAP_OPENNI_IR_GENERATOR_PRESENT            = CV_CAP_OPENNI_IR_GENERATOR + CV_CAP_PROP_OPENNI_GENERATOR_PRESENT;

    # Properties of cameras available through GStreamer interface
    CV_CAP_GSTREAMER_QUEUE_LENGTH           = 200; # default is 1

    # PVAPI
    CV_CAP_PROP_PVAPI_MULTICASTIP           = 300; # ip for anable multicast master mode. 0 for disable multicast
    CV_CAP_PROP_PVAPI_FRAMESTARTTRIGGERMODE = 301; # FrameStartTriggerMode: Determines how a frame is initiated
    CV_CAP_PROP_PVAPI_DECIMATIONHORIZONTAL  = 302; # Horizontal sub-sampling of the image
    CV_CAP_PROP_PVAPI_DECIMATIONVERTICAL    = 303; # Vertical sub-sampling of the image
    CV_CAP_PROP_PVAPI_BINNINGX              = 304; # Horizontal binning factor
    CV_CAP_PROP_PVAPI_BINNINGY              = 305; # Vertical binning factor
    CV_CAP_PROP_PVAPI_PIXELFORMAT           = 306; # Pixel format

    # Properties of cameras available through XIMEA SDK interface
    CV_CAP_PROP_XI_DOWNSAMPLING                                 = 400; # Change image resolution by binning or skipping.
    CV_CAP_PROP_XI_DATA_FORMAT                                  = 401; # Output data format.
    CV_CAP_PROP_XI_OFFSET_X                                     = 402; # Horizontal offset from the origin to the area of interest (in pixels).
    CV_CAP_PROP_XI_OFFSET_Y                                     = 403; # Vertical offset from the origin to the area of interest (in pixels).
    CV_CAP_PROP_XI_TRG_SOURCE                                   = 404; # Defines source of trigger.
    CV_CAP_PROP_XI_TRG_SOFTWARE                                 = 405; # Generates an internal trigger. PRM_TRG_SOURCE must be set to TRG_SOFTWARE.
    CV_CAP_PROP_XI_GPI_SELECTOR                                 = 406; # Selects general purpose input
    CV_CAP_PROP_XI_GPI_MODE                                     = 407; # Set general purpose input mode
    CV_CAP_PROP_XI_GPI_LEVEL                                    = 408; # Get general purpose level
    CV_CAP_PROP_XI_GPO_SELECTOR                                 = 409; # Selects general purpose output
    CV_CAP_PROP_XI_GPO_MODE                                     = 410; # Set general purpose output mode
    CV_CAP_PROP_XI_LED_SELECTOR                                 = 411; # Selects camera signalling LED
    CV_CAP_PROP_XI_LED_MODE                                     = 412; # Define camera signalling LED functionality
    CV_CAP_PROP_XI_MANUAL_WB                                    = 413; # Calculates White Balance(must be called during acquisition)
    CV_CAP_PROP_XI_AUTO_WB                                      = 414; # Automatic white balance
    CV_CAP_PROP_XI_AEAG                                         = 415; # Automatic exposure/gain
    CV_CAP_PROP_XI_EXP_PRIORITY                                 = 416; # Exposure priority (0.5 - exposure 50%; gain 50%).
    CV_CAP_PROP_XI_AE_MAX_LIMIT                                 = 417; # Maximum limit of exposure in AEAG procedure
    CV_CAP_PROP_XI_AG_MAX_LIMIT                                 = 418;  # Maximum limit of gain in AEAG procedure
    CV_CAP_PROP_XI_AEAG_LEVEL                                   = 419; # Average intensity of output signal AEAG should achieve(in %)
    CV_CAP_PROP_XI_TIMEOUT                                      = 420; # Image capture timeout in milliseconds
    CV_CAP_PROP_XI_EXPOSURE                                     = 421; # Exposure time in microseconds
    CV_CAP_PROP_XI_EXPOSURE_BURST_COUNT                         = 422; # Sets the number of times of exposure in one frame.
    CV_CAP_PROP_XI_GAIN_SELECTOR                                = 423; # Gain selector for parameter Gain allows to select different type of gains.
    CV_CAP_PROP_XI_GAIN                                         = 424; # Gain in dB
    CV_CAP_PROP_XI_DOWNSAMPLING_TYPE                            = 426; # Change image downsampling type.
    CV_CAP_PROP_XI_BINNING_SELECTOR                             = 427; # Binning engine selector.
    CV_CAP_PROP_XI_BINNING_VERTICAL                             = 428; # Vertical Binning - number of vertical photo-sensitive cells to combine together.
    CV_CAP_PROP_XI_BINNING_HORIZONTAL                           = 429; # Horizontal Binning - number of horizontal photo-sensitive cells to combine together.
    CV_CAP_PROP_XI_BINNING_PATTERN                              = 430; # Binning pattern type.
    CV_CAP_PROP_XI_DECIMATION_SELECTOR                          = 431; # Decimation engine selector.
    CV_CAP_PROP_XI_DECIMATION_VERTICAL                          = 432; # Vertical Decimation - vertical sub-sampling of the image - reduces the vertical resolution of the image by the specified vertical decimation factor.
    CV_CAP_PROP_XI_DECIMATION_HORIZONTAL                        = 433; # Horizontal Decimation - horizontal sub-sampling of the image - reduces the horizontal resolution of the image by the specified vertical decimation factor.
    CV_CAP_PROP_XI_DECIMATION_PATTERN                           = 434; # Decimation pattern type.
    CV_CAP_PROP_XI_TEST_PATTERN_GENERATOR_SELECTOR              = 587; # Selects which test pattern generator is controlled by the TestPattern feature.
    CV_CAP_PROP_XI_TEST_PATTERN                                 = 588; # Selects which test pattern type is generated by the selected generator.
    CV_CAP_PROP_XI_IMAGE_DATA_FORMAT                            = 435; # Output data format.
    CV_CAP_PROP_XI_SHUTTER_TYPE                                 = 436; # Change sensor shutter type(CMOS sensor).
    CV_CAP_PROP_XI_SENSOR_TAPS                                  = 437; # Number of taps
    CV_CAP_PROP_XI_AEAG_ROI_OFFSET_X                            = 439; # Automatic exposure/gain ROI offset X
    CV_CAP_PROP_XI_AEAG_ROI_OFFSET_Y                            = 440; # Automatic exposure/gain ROI offset Y
    CV_CAP_PROP_XI_AEAG_ROI_WIDTH                               = 441; # Automatic exposure/gain ROI Width
    CV_CAP_PROP_XI_AEAG_ROI_HEIGHT                              = 442; # Automatic exposure/gain ROI Height
    CV_CAP_PROP_XI_BPC                                          = 445; # Correction of bad pixels
    CV_CAP_PROP_XI_WB_KR                                        = 448; # White balance red coefficient
    CV_CAP_PROP_XI_WB_KG                                        = 449; # White balance green coefficient
    CV_CAP_PROP_XI_WB_KB                                        = 450; # White balance blue coefficient
    CV_CAP_PROP_XI_WIDTH                                        = 451; # Width of the Image provided by the device (in pixels).
    CV_CAP_PROP_XI_HEIGHT                                       = 452; # Height of the Image provided by the device (in pixels).
    CV_CAP_PROP_XI_REGION_SELECTOR                              = 589; # Selects Region in Multiple ROI which parameters are set by width; height; ... ;region mode
    CV_CAP_PROP_XI_REGION_MODE                                  = 595; # Activates/deactivates Region selected by Region Selector
    CV_CAP_PROP_XI_LIMIT_BANDWIDTH                              = 459; # Set/get bandwidth(datarate)(in Megabits)
    CV_CAP_PROP_XI_SENSOR_DATA_BIT_DEPTH                        = 460; # Sensor output data bit depth.
    CV_CAP_PROP_XI_OUTPUT_DATA_BIT_DEPTH                        = 461; # Device output data bit depth.
    CV_CAP_PROP_XI_IMAGE_DATA_BIT_DEPTH                         = 462; # bitdepth of data returned by function xiGetImage
    CV_CAP_PROP_XI_OUTPUT_DATA_PACKING                          = 463; # Device output data packing (or grouping) enabled. Packing could be enabled if output_data_bit_depth > 8 and packing capability is available.
    CV_CAP_PROP_XI_OUTPUT_DATA_PACKING_TYPE                     = 464; # Data packing type. Some cameras supports only specific packing type.
    CV_CAP_PROP_XI_IS_COOLED                                    = 465; # Returns 1 for cameras that support cooling.
    CV_CAP_PROP_XI_COOLING                                      = 466; # Start camera cooling.
    CV_CAP_PROP_XI_TARGET_TEMP                                  = 467; # Set sensor target temperature for cooling.
    CV_CAP_PROP_XI_CHIP_TEMP                                    = 468; # Camera sensor temperature
    CV_CAP_PROP_XI_HOUS_TEMP                                    = 469; # Camera housing tepmerature
    CV_CAP_PROP_XI_HOUS_BACK_SIDE_TEMP                          = 590; # Camera housing back side tepmerature
    CV_CAP_PROP_XI_SENSOR_BOARD_TEMP                            = 596; # Camera sensor board temperature
    CV_CAP_PROP_XI_CMS                                          = 470; # Mode of color management system.
    CV_CAP_PROP_XI_APPLY_CMS                                    = 471; # Enable applying of CMS profiles to xiGetImage (see XI_PRM_INPUT_CMS_PROFILE; XI_PRM_OUTPUT_CMS_PROFILE).
    CV_CAP_PROP_XI_IMAGE_IS_COLOR                               = 474; # Returns 1 for color cameras.
    CV_CAP_PROP_XI_COLOR_FILTER_ARRAY                           = 475; # Returns color filter array type of RAW data.
    CV_CAP_PROP_XI_GAMMAY                                       = 476; # Luminosity gamma
    CV_CAP_PROP_XI_GAMMAC                                       = 477; # Chromaticity gamma
    CV_CAP_PROP_XI_SHARPNESS                                    = 478; # Sharpness Strength
    CV_CAP_PROP_XI_CC_MATRIX_00                                 = 479; # Color Correction Matrix element [0][0]
    CV_CAP_PROP_XI_CC_MATRIX_01                                 = 480; # Color Correction Matrix element [0][1]
    CV_CAP_PROP_XI_CC_MATRIX_02                                 = 481; # Color Correction Matrix element [0][2]
    CV_CAP_PROP_XI_CC_MATRIX_03                                 = 482; # Color Correction Matrix element [0][3]
    CV_CAP_PROP_XI_CC_MATRIX_10                                 = 483; # Color Correction Matrix element [1][0]
    CV_CAP_PROP_XI_CC_MATRIX_11                                 = 484; # Color Correction Matrix element [1][1]
    CV_CAP_PROP_XI_CC_MATRIX_12                                 = 485; # Color Correction Matrix element [1][2]
    CV_CAP_PROP_XI_CC_MATRIX_13                                 = 486; # Color Correction Matrix element [1][3]
    CV_CAP_PROP_XI_CC_MATRIX_20                                 = 487; # Color Correction Matrix element [2][0]
    CV_CAP_PROP_XI_CC_MATRIX_21                                 = 488; # Color Correction Matrix element [2][1]
    CV_CAP_PROP_XI_CC_MATRIX_22                                 = 489; # Color Correction Matrix element [2][2]
    CV_CAP_PROP_XI_CC_MATRIX_23                                 = 490; # Color Correction Matrix element [2][3]
    CV_CAP_PROP_XI_CC_MATRIX_30                                 = 491; # Color Correction Matrix element [3][0]
    CV_CAP_PROP_XI_CC_MATRIX_31                                 = 492; # Color Correction Matrix element [3][1]
    CV_CAP_PROP_XI_CC_MATRIX_32                                 = 493; # Color Correction Matrix element [3][2]
    CV_CAP_PROP_XI_CC_MATRIX_33                                 = 494; # Color Correction Matrix element [3][3]
    CV_CAP_PROP_XI_DEFAULT_CC_MATRIX                            = 495; # Set default Color Correction Matrix
    CV_CAP_PROP_XI_TRG_SELECTOR                                 = 498; # Selects the type of trigger.
    CV_CAP_PROP_XI_ACQ_FRAME_BURST_COUNT                        = 499; # Sets number of frames acquired by burst. This burst is used only if trigger is set to FrameBurstStart
    CV_CAP_PROP_XI_DEBOUNCE_EN                                  = 507; # Enable/Disable debounce to selected GPI
    CV_CAP_PROP_XI_DEBOUNCE_T0                                  = 508; # Debounce time (x * 10us)
    CV_CAP_PROP_XI_DEBOUNCE_T1                                  = 509; # Debounce time (x * 10us)
    CV_CAP_PROP_XI_DEBOUNCE_POL                                 = 510; # Debounce polarity (pol = 1 t0 - falling edge; t1 - rising edge)
    CV_CAP_PROP_XI_LENS_MODE                                    = 511; # Status of lens control interface. This shall be set to XI_ON before any Lens operations.
    CV_CAP_PROP_XI_LENS_APERTURE_VALUE                          = 512; # Current lens aperture value in stops. Examples: 2.8; 4; 5.6; 8; 11
    CV_CAP_PROP_XI_LENS_FOCUS_MOVEMENT_VALUE                    = 513; # Lens current focus movement value to be used by XI_PRM_LENS_FOCUS_MOVE in motor steps.
    CV_CAP_PROP_XI_LENS_FOCUS_MOVE                              = 514; # Moves lens focus motor by steps set in XI_PRM_LENS_FOCUS_MOVEMENT_VALUE.
    CV_CAP_PROP_XI_LENS_FOCUS_DISTANCE                          = 515; # Lens focus distance in cm.
    CV_CAP_PROP_XI_LENS_FOCAL_LENGTH                            = 516; # Lens focal distance in mm.
    CV_CAP_PROP_XI_LENS_FEATURE_SELECTOR                        = 517; # Selects the current feature which is accessible by XI_PRM_LENS_FEATURE.
    CV_CAP_PROP_XI_LENS_FEATURE                                 = 518; # Allows access to lens feature value currently selected by XI_PRM_LENS_FEATURE_SELECTOR.
    CV_CAP_PROP_XI_DEVICE_MODEL_ID                              = 521; # Return device model id
    CV_CAP_PROP_XI_DEVICE_SN                                    = 522; # Return device serial number
    CV_CAP_PROP_XI_IMAGE_DATA_FORMAT_RGB32_ALPHA                = 529; # The alpha channel of RGB32 output image format.
    CV_CAP_PROP_XI_IMAGE_PAYLOAD_SIZE                           = 530; # Buffer size in bytes sufficient for output image returned by xiGetImage
    CV_CAP_PROP_XI_TRANSPORT_PIXEL_FORMAT                       = 531; # Current format of pixels on transport layer.
    CV_CAP_PROP_XI_SENSOR_CLOCK_FREQ_HZ                         = 532; # Sensor clock frequency in Hz.
    CV_CAP_PROP_XI_SENSOR_CLOCK_FREQ_INDEX                      = 533; # Sensor clock frequency index. Sensor with selected frequencies have possibility to set the frequency only by this index.
    CV_CAP_PROP_XI_SENSOR_OUTPUT_CHANNEL_COUNT                  = 534; # Number of output channels from sensor used for data transfer.
    CV_CAP_PROP_XI_FRAMERATE                                    = 535; # Define framerate in Hz
    CV_CAP_PROP_XI_COUNTER_SELECTOR                             = 536; # Select counter
    CV_CAP_PROP_XI_COUNTER_VALUE                                = 537; # Counter status
    CV_CAP_PROP_XI_ACQ_TIMING_MODE                              = 538; # Type of sensor frames timing.
    CV_CAP_PROP_XI_AVAILABLE_BANDWIDTH                          = 539; # Calculate and return available interface bandwidth(int Megabits)
    CV_CAP_PROP_XI_BUFFER_POLICY                                = 540; # Data move policy
    CV_CAP_PROP_XI_LUT_EN                                       = 541; # Activates LUT.
    CV_CAP_PROP_XI_LUT_INDEX                                    = 542; # Control the index (offset) of the coefficient to access in the LUT.
    CV_CAP_PROP_XI_LUT_VALUE                                    = 543; # Value at entry LUTIndex of the LUT
    CV_CAP_PROP_XI_TRG_DELAY                                    = 544; # Specifies the delay in microseconds (us) to apply after the trigger reception before activating it.
    CV_CAP_PROP_XI_TS_RST_MODE                                  = 545; # Defines how time stamp reset engine will be armed
    CV_CAP_PROP_XI_TS_RST_SOURCE                                = 546; # Defines which source will be used for timestamp reset. Writing this parameter will trigger settings of engine (arming)
    CV_CAP_PROP_XI_IS_DEVICE_EXIST                              = 547; # Returns 1 if camera connected and works properly.
    CV_CAP_PROP_XI_ACQ_BUFFER_SIZE                              = 548; # Acquisition buffer size in buffer_size_unit. Default bytes.
    CV_CAP_PROP_XI_ACQ_BUFFER_SIZE_UNIT                         = 549; # Acquisition buffer size unit in bytes. Default 1. E.g. Value 1024 means that buffer_size is in KiBytes
    CV_CAP_PROP_XI_ACQ_TRANSPORT_BUFFER_SIZE                    = 550; # Acquisition transport buffer size in bytes
    CV_CAP_PROP_XI_BUFFERS_QUEUE_SIZE                           = 551; # Queue of field/frame buffers
    CV_CAP_PROP_XI_ACQ_TRANSPORT_BUFFER_COMMIT                  = 552; # Number of buffers to commit to low level
    CV_CAP_PROP_XI_RECENT_FRAME                                 = 553; # GetImage returns most recent frame
    CV_CAP_PROP_XI_DEVICE_RESET                                 = 554; # Resets the camera to default state.
    CV_CAP_PROP_XI_COLUMN_FPN_CORRECTION                        = 555; # Correction of column FPN
    CV_CAP_PROP_XI_ROW_FPN_CORRECTION                           = 591; # Correction of row FPN
    CV_CAP_PROP_XI_SENSOR_MODE                                  = 558; # Current sensor mode. Allows to select sensor mode by one integer. Setting of this parameter affects: image dimensions and downsampling.
    CV_CAP_PROP_XI_HDR                                          = 559; # Enable High Dynamic Range feature.
    CV_CAP_PROP_XI_HDR_KNEEPOINT_COUNT                          = 560; # The number of kneepoints in the PWLR.
    CV_CAP_PROP_XI_HDR_T1                                       = 561; # position of first kneepoint(in % of XI_PRM_EXPOSURE)
    CV_CAP_PROP_XI_HDR_T2                                       = 562; # position of second kneepoint (in % of XI_PRM_EXPOSURE)
    CV_CAP_PROP_XI_KNEEPOINT1                                   = 563; # value of first kneepoint (% of sensor saturation)
    CV_CAP_PROP_XI_KNEEPOINT2                                   = 564; # value of second kneepoint (% of sensor saturation)
    CV_CAP_PROP_XI_IMAGE_BLACK_LEVEL                            = 565; # Last image black level counts. Can be used for Offline processing to recall it.
    CV_CAP_PROP_XI_HW_REVISION                                  = 571; # Returns hardware revision number.
    CV_CAP_PROP_XI_DEBUG_LEVEL                                  = 572; # Set debug level
    CV_CAP_PROP_XI_AUTO_BANDWIDTH_CALCULATION                   = 573; # Automatic bandwidth calculation;
    CV_CAP_PROP_XI_FFS_FILE_ID                                  = 594; # File number.
    CV_CAP_PROP_XI_FFS_FILE_SIZE                                = 580; # Size of file.
    CV_CAP_PROP_XI_FREE_FFS_SIZE                                = 581; # Size of free camera FFS.
    CV_CAP_PROP_XI_USED_FFS_SIZE                                = 582; # Size of used camera FFS.
    CV_CAP_PROP_XI_FFS_ACCESS_KEY                               = 583; # Setting of key enables file operations on some cameras.
    CV_CAP_PROP_XI_SENSOR_FEATURE_SELECTOR                      = 585; # Selects the current feature which is accessible by XI_PRM_SENSOR_FEATURE_VALUE.
    CV_CAP_PROP_XI_SENSOR_FEATURE_VALUE                         = 586; # Allows access to sensor feature value currently selected by XI_PRM_SENSOR_FEATURE_SELECTOR.


    # Properties for Android cameras
    CV_CAP_PROP_ANDROID_FLASH_MODE = 8001;
    CV_CAP_PROP_ANDROID_FOCUS_MODE = 8002;
    CV_CAP_PROP_ANDROID_WHITE_BALANCE = 8003;
    CV_CAP_PROP_ANDROID_ANTIBANDING = 8004;
    CV_CAP_PROP_ANDROID_FOCAL_LENGTH = 8005;
    CV_CAP_PROP_ANDROID_FOCUS_DISTANCE_NEAR = 8006;
    CV_CAP_PROP_ANDROID_FOCUS_DISTANCE_OPTIMAL = 8007;
    CV_CAP_PROP_ANDROID_FOCUS_DISTANCE_FAR = 8008;
    CV_CAP_PROP_ANDROID_EXPOSE_LOCK = 8009;
    CV_CAP_PROP_ANDROID_WHITEBALANCE_LOCK = 8010;

    # Properties of cameras available through AVFOUNDATION interface
    CV_CAP_PROP_IOS_DEVICE_FOCUS = 9001;
    CV_CAP_PROP_IOS_DEVICE_EXPOSURE = 9002;
    CV_CAP_PROP_IOS_DEVICE_FLASH = 9003;
    CV_CAP_PROP_IOS_DEVICE_WHITEBALANCE = 9004;
    CV_CAP_PROP_IOS_DEVICE_TORCH = 9005;

    # Properties of cameras available through Smartek Giganetix Ethernet Vision interface
    #* --- Vladimir Litvinenko (litvinenko.vladimir@gmail.com) --- */
    CV_CAP_PROP_GIGA_FRAME_OFFSET_X = 10001;
    CV_CAP_PROP_GIGA_FRAME_OFFSET_Y = 10002;
    CV_CAP_PROP_GIGA_FRAME_WIDTH_MAX = 10003;
    CV_CAP_PROP_GIGA_FRAME_HEIGH_MAX = 10004;
    CV_CAP_PROP_GIGA_FRAME_SENS_WIDTH = 10005;
    CV_CAP_PROP_GIGA_FRAME_SENS_HEIGH = 10006;

    CV_CAP_PROP_INTELPERC_PROFILE_COUNT               = 11001;
    CV_CAP_PROP_INTELPERC_PROFILE_IDX                 = 11002;
    CV_CAP_PROP_INTELPERC_DEPTH_LOW_CONFIDENCE_VALUE  = 11003;
    CV_CAP_PROP_INTELPERC_DEPTH_SATURATION_VALUE      = 11004;
    CV_CAP_PROP_INTELPERC_DEPTH_CONFIDENCE_THRESHOLD  = 11005;
    CV_CAP_PROP_INTELPERC_DEPTH_FOCAL_LENGTH_HORZ     = 11006;
    CV_CAP_PROP_INTELPERC_DEPTH_FOCAL_LENGTH_VERT     = 11007;

    # Intel PerC streams
    CV_CAP_INTELPERC_DEPTH_GENERATOR = 1 << 29;
    CV_CAP_INTELPERC_IMAGE_GENERATOR = 1 << 28;
    CV_CAP_INTELPERC_GENERATORS_MASK = CV_CAP_INTELPERC_DEPTH_GENERATOR + CV_CAP_INTELPERC_IMAGE_GENERATOR

    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]

class DAQ_2DViewer_OpenCVCam(DAQ_Viewer_base):
    """
        =============== ==================
        **Attributes**   **Type**
        *params*         dictionnary list
        *x_axis*         1D numpy array
        *y_axis*         1D numpy array
        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """

    params= comon_parameters+[{'title': 'Camera index:', 'name': 'camera_index', 'type': 'int', 'value': 0 , 'default':0, 'min': 0},
                              {'title': 'Colors:', 'name': 'colors', 'type': 'list', 'value': 'gray' , 'values': ['gray','RGB']},
                              {'title': 'Open Settings:', 'name': 'open_settings', 'type': 'bool', 'value': False },
                              ]
    hardware_averaging = False

    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_2DViewer_OpenCVCam,self).__init__(parent,params_state)
        self.x_axis=None
        self.y_axis=None



    def commit_settings(self,param):
        """
            Activate parameters changes on the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                          **Description**
            *param*          instance of pyqtgraph Parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            
        """
        try:
            if param.name()=='open_settings':
                if param.value():
                    self.controller.set(OpenCVProp['CV_CAP_PROP_SETTINGS'].value,0)
                    param.setValue(False)
            else:
                self.controller.set(OpenCVProp['CV_CAP_'+param.name()].value,param.value())
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))



    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector initializing the status dictionnary.

            See Also
            --------
            DAQ_utils.ThreadCommand, get_xaxis, get_yaxis
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:

            if self.settings.child(('controller_status')).value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller=controller
            else:
                self.controller=cv2.VideoCapture(self.settings.child(('camera_index')).value())

            #self.get_active_properties() #to add settable settings to the param list (but driver builtin settings window is prefered (OpenCVProp['CV_CAP_PROP_SETTINGS'])


            self.x_axis=self.get_xaxis()
            self.y_axis=self.get_yaxis()



            self.status.x_axis=self.x_axis
            self.status.y_axis=self.y_axis
            self.status.initialized=True
            self.status.controller=self.controller
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status


    def get_active_properties(self):
        props=OpenCVProp.names()
        self.additional_params=[]
        for prop in props:
            try:
                ret=self.controller.get(OpenCVProp[prop].value)
                if ret!=-1:
                    try:
                        ret_set=self.controller.set(OpenCVProp[prop].value,ret)
                    except:
                        ret_set=False
                    self.additional_params.append({'title': prop[7:], 'name': prop[7:], 'type': 'int', 'value': ret, 'readonly': not ret_set})
            except:
                pass
        self.settings.addChildren(self.additional_params)
        pass

    def Close(self):
        """
            not implemented.
        """
        try:
            for child_dict in self.additional_params:
                self.settings.removeChild(self.settings.child((child_dict['name'])))
            self.controller.release()
        except :
            pass

    def get_xaxis(self):
        """
            Get the current x_axis from the Mock data setting.

            Returns
            -------
            1D numpy array
                the current x_axis.

            See Also
            --------
            
        """
        Nx=self.controller.get(3) #property index corresponding to width
        self.x_axis=np.linspace(0,Nx-1,Nx)
        return self.x_axis

    def get_yaxis(self):
        """
            Get the current y_axis from the Mock data setting.

            Returns
            -------
            1D numpy array
                the current y_axis.

            See Also
            --------
            
        """
        Ny=self.controller.get(4) #property index corresponding to width
        self.y_axis=np.linspace(0,Ny-1,Ny)
        return self.y_axis
        return self.y_axis

    def Grab(self,Naverage=1,**kwargs):
        """
            | For each integer step of naverage range set mock data.
            | Construct the data matrix and send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       The number of images to average.
                                      specify the threshold of the mean calculation
            =============== ======== ===============================================

            See Also
            --------
            set_Mock_data
        """
        ret,frame=self.controller.read()
        QThread.msleep(200)
        if ret:
            if self.settings.child(('colors')).value()=='gray':
                data_cam = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)]
                data_cam[0]=data_cam[0].astype(np.float32)
            else:
                if len(frame.shape)==3:
                    data_cam=[frame[:,:,ind] for ind in range(frame.shape[2])]
                else:
                    data_cam = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)]

        else:
            raise Exception('no return from the controller')

        data=[OrderedDict(name='OpenCV',data=data_cam, type='Data2D')]

        self.data_grabed_signal.emit(data)

    def Stop(self):
        """
            not implemented.
        """

        return ""
