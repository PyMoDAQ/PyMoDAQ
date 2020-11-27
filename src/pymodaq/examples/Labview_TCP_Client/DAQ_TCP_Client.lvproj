<?xml version='1.0' encoding='UTF-8'?>
<Project Type="Project" LVVersion="15008000">
	<Item Name="My Computer" Type="My Computer">
		<Property Name="server.app.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.control.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.tcp.enabled" Type="Bool">false</Property>
		<Property Name="server.tcp.port" Type="Int">0</Property>
		<Property Name="server.tcp.serviceName" Type="Str">My Computer/VI Server</Property>
		<Property Name="server.tcp.serviceName.default" Type="Str">My Computer/VI Server</Property>
		<Property Name="server.vi.callsEnabled" Type="Bool">true</Property>
		<Property Name="server.vi.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="specify.custom.address" Type="Bool">false</Property>
		<Item Name="controls" Type="Folder">
			<Item Name="client_state.ctl" Type="VI" URL="../client_state.ctl"/>
			<Item Name="cmd_types.ctl" Type="VI" URL="../cmd_types.ctl"/>
		</Item>
		<Item Name="subvis" Type="Folder">
			<Item Name="DAQ_TCP_read_cmd.vi" Type="VI" URL="../DAQ_TCP_read_cmd.vi"/>
			<Item Name="DAQ_TCP_send_data.vi" Type="VI" URL="../DAQ_TCP_send_data.vi"/>
			<Item Name="DAQ_TCP_send_int.vi" Type="VI" URL="../DAQ_TCP_send_int.vi"/>
			<Item Name="DAQ_TCP_send_string.vi" Type="VI" URL="../DAQ_TCP_send_string.vi"/>
			<Item Name="DAQ_TCP_Server_1Dgaussian.vi" Type="VI" URL="../DAQ_TCP_Server_1Dgaussian.vi"/>
			<Item Name="DAQ_TCP_Server_2Dgaussian.vi" Type="VI" URL="../DAQ_TCP_Server_2Dgaussian.vi"/>
		</Item>
		<Item Name="DAQ_TCP_Client.vi" Type="VI" URL="../DAQ_TCP_Client.vi"/>
		<Item Name="Dependencies" Type="Dependencies"/>
		<Item Name="Build Specifications" Type="Build"/>
	</Item>
</Project>
