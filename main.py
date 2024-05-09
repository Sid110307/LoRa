#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
import socket
import threading
from datetime import datetime

import sounddevice as sd
import numpy as np

host = "localhost"
port = 12345


class App:
    def __init__(self, master):
        self.master = master
        master.title("LoRa")

        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, padx=10, pady=10)

        self.tab_io = ttk.Frame(self.notebook)
        self.tab_commands = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_io, text="IO")
        self.notebook.add(self.tab_commands, text="Commands")
        self.notebook.add(self.tab_settings, text="Settings")

        self.setup_io_tab()
        self.setup_settings_tab()
        self.setup_commands_tab()

        self.logger = tk.Text(master, state=tk.DISABLED)
        self.logger.grid(row=0, column=1, padx=10, pady=10)
        self.log("Ready to communicate." if self.send("AT", False)
                 == "OK" else "Error initializing communication.")

    def setup_io_tab(self):
        ttk.Label(self.tab_io, text="Text:").grid(
            row=0, column=0, padx=10, pady=10)
        self.text_entry = ttk.Entry(self.tab_io)
        self.text_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Button(self.tab_io, text="Send Text", command=lambda: threading.Thread(
            target=self.send, args=(self.text_entry.get(),)).start()).grid(row=0, column=2, padx=10, pady=10)
        ttk.Button(self.tab_io, text="Send Audio", command=self.send_audio).grid(
            row=1, column=1, padx=10, pady=10)
        ttk.Button(self.tab_io, text="Test Connection", command=lambda: threading.Thread(
            target=self.send, args=("AT",)).start()).grid(row=1, column=2, padx=10, pady=10)
        ttk.Button(self.tab_io, text="Clear Log", command=self.clear_log).grid(
            row=1, column=0, padx=10, pady=10)

    def setup_settings_tab(self):
        ttk.Label(self.tab_settings, text="Host:").grid(
            row=0, column=0, padx=10, pady=10)
        self.host_entry = ttk.Entry(self.tab_settings)
        self.host_entry.insert(0, host)
        self.host_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(self.tab_settings, text="Port:").grid(
            row=1, column=0, padx=10, pady=10)
        self.port_entry = ttk.Entry(self.tab_settings)
        self.port_entry.insert(0, str(port))
        self.port_entry.grid(row=1, column=1, padx=10, pady=10)

        ttk.Button(self.tab_settings, text="Apply Settings", command=self.apply_settings).grid(
            row=2, column=0, columnspan=2, pady=10)

    def apply_settings(self):
        global host, port

        host = self.host_entry.get()
        port = int(self.port_entry.get())
        self.log("Settings updated: Host=" + host + ", Port=" + str(port))

    def setup_commands_tab(self):
        commands = {
            "AT": """AT
===============

Syntax: AT
Parameters: None

Tests the communication between the module and the host. The module will respond with "OK" if the communication is successful.
""",

            "AT+ADDRESS": """AT+ADDRESS
===============

Syntax: AT+ADDRESS=<Address>
Parameters: Address (0-65535)

Sets the ADDRESS of the module. This ADDRESS acts as the identification for the transmitter or a specific receiver. The address range is from 0 to 65535, with the default being 0.
""",

            "AT+ADDRESS?": """AT+ADDRESS?
===============

Syntax: AT+ADDRESS?
Parameters: None

Inquires about the ADDRESS of the module. The ADDRESS acts as the identification for the transmitter or a specific receiver.
""",

            "AT+NETWORKID": """AT+NETWORKID
===============

Syntax: AT+NETWORKID=<Network ID>
Parameters: Network ID (0-16)

Sets the ID of the Lora network, which is essential for group communication. Only modules with the same NETWORKID can communicate. The NETWORKID ranges from 0 to 16, where "0" is the public ID and typically avoided to ensure distinct network identification.
""",

            "AT+NETWORKID?": """AT+NETWORKID?
===============

Syntax: AT+NETWORKID?
Parameters: None

Inquires about the ID of the Lora network. This ID is essential for group communication, with only modules sharing the same NETWORKID able to communicate.
""",

            "AT+BAND": """AT+BAND
===============

Syntax: AT+BAND=<Frequency>
Parameters: Frequency (Hertz)

Sets the center frequency of the wireless band, requiring both the transmitter and receiver to operate on the same frequency for successful communication. Frequency is set in Hertz.
""",

            "AT+BAND?": """AT+BAND?
===============

Syntax: AT+BAND?
Parameters: None

Inquires about the center frequency of the wireless band. This frequency must match between the transmitter and receiver for successful communication.
""",

            "AT+PARAMETER": """AT+PARAMETER
===============

Syntax: AT+PARAMETER=<Spreading Factor>,<Bandwidth>,<Coding Rate>,<Programmed Preamble>
Parameters: Spreading Factor (7-12), Bandwidth (0-2), Coding Rate (1-4), Programmed Preamble (0-65535)

Sets the RF wireless parameters including Spreading Factor, Bandwidth, Coding Rate, and Programmed Preamble. These parameters must match between the transmitter and receiver to ensure communication.
""",

            "AT+PARAMETER?": """AT+PARAMETER?
===============

Syntax: AT+PARAMETER?
Parameters: None

Inquires about the RF wireless parameters including Spreading Factor, Bandwidth, Coding Rate, and Programmed Preamble. These parameters must match between the transmitter and receiver to ensure communication.
""",

            "AT+SEND": """AT+SEND
===============

Syntax: AT+SEND=<Address>,<Payload Length>,<Data>
Parameters: Address (0-65535), Payload Length (0-255), Data (ASCII)

Sends data to the specified ADDRESS. The command includes the payload length and the data in ASCII format. Note that the actual data length sent will be the specified payload length plus an additional 8 bytes.
""",

            "AT+MODE": """AT+MODE
===============

Syntax: AT+MODE=<Mode>
Parameters: Mode (0 = Transmit and Receive, 1 = Sleep)

Sets the working mode of the module. Mode "0" is the default Transmit and Receive mode, while mode "1" sets the module to Sleep mode, which can be awakened by data on pin3 (RX).
""",

            "AT+MODE?": """AT+MODE?
===============

Syntax: AT+MODE?
Parameters: None

Inquires about the working mode of the module. Mode "0" is the default Transmit and Receive mode, while mode "1" sets the module to Sleep mode.
""",

            "AT+IPR": """AT+IPR
===============

Syntax: AT+IPR=<Rate>
Parameters: Rate (300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200)

Sets the UART baud rate. The rate must be one of the predefined values (300 to 115200). The setting is saved in EEPROM, and 115200 is the default rate.
""",

            "AT+IPR?": """AT+IPR?
===============

Syntax: AT+IPR?
Parameters: None

Inquires about the UART baud rate. The rate must be one of the predefined values (300 to 115200).
""",

            "AT+CPIN": """AT+CPIN
===============

Syntax: AT+CPIN=<Password>
Parameters: Password (AES128)

Sets the AES128 password for network security. This password allows the data to be recognized by other modules within the network. If the module is reset, the password must be set again.
""",

            "AT+CPIN?": """AT+CPIN?
===============

Syntax: AT+CPIN?
Parameters: None

Inquires about the AES128 password for network security. This password allows the data to be recognized by other modules within the network.
""",

            "AT+CRFOP": """AT+CRFOP
===============

Syntax: AT+CRFOP=<Power>
Parameters: Power (0-15)

Sets the RF output power level of the module. The power level ranges from 0 (0 dBm) to 15 (15 dBm), with the default set to the maximum 15 dBm.
""",

            "AT+CRFOP?": """AT+CRFOP?
===============

Syntax: AT+CRFOP?
Parameters: None

Inquires about the RF output power level of the module. The power level ranges from 0 (0 dBm) to 15 (15 dBm).
""",

            "+RCV": """+RCV
===============

Syntax: +RCV=<Address>,<Length>,<Data>,<RSSI>,<SNR>
Parameters: Address (0-65535), Length (0-255), Data (ASCII), RSSI (dBm), SNR (dB)

Displays data received by the module. Includes details such as the Address ID of the transmitter, the length and content of the data, the Received Signal Strength Indicator (RSSI), and the Signal-to-Noise Ratio (SNR).
""",

            "AT+VER?": """AT+VER?
===============

Syntax: AT+VER?
Parameters: None

Inquires about the firmware version of the module. The command returns the version details specific to the module type, either RYLR40x or RYLR89x.
""",

            "AT+UID?": """AT+UID?
===============

Syntax: AT+UID?
Parameters: None

Inquires about the unique ID number of the module. This is a 12-byte identifier that is unique to each module.
""",

            "AT+FACTORY": """AT+FACTORY
===============

Syntax: AT+FACTORY
Parameters: None

Resets all parameters to their manufacturer default settings. This includes frequency, UART rate, spreading factor, bandwidth, coding rate, preamble length, address, network ID, and RF output power.
"""
        }

        ttk.Label(self.tab_commands, text="Preset Commands:").grid(
            row=0, column=0, padx=10, pady=10)
        self.preset_commands = ttk.Combobox(
            self.tab_commands, values=list(commands.keys()))
        self.preset_commands.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(self.tab_commands, text="Parameters:").grid(
            row=0, column=2, padx=10, pady=10)
        self.param_entry = ttk.Entry(self.tab_commands)
        self.param_entry.grid(row=0, column=3, padx=10, pady=10)

        ttk.Button(self.tab_commands, text="Send", command=lambda: threading.Thread(target=self.send, args=(self.preset_commands.get(
        ) + ("=" + self.param_entry.get() if self.param_entry.get() else ""),)).start()).grid(row=1, column=0, columnspan=4, padx=10, pady=10)

        self.command_info = tk.Text(
            self.tab_commands, state=tk.DISABLED, wrap=tk.WORD)
        self.command_info.grid(row=2, column=0, columnspan=4, padx=10, pady=10)

        def on_preset_command_selected(event):
            command = self.preset_commands.get()
            self.command_info.config(state=tk.NORMAL)
            self.command_info.delete("1.0", tk.END)
            self.command_info.insert(tk.END, commands[command])
            self.command_info.config(state=tk.DISABLED)

        self.preset_commands.bind(
            "<<ComboboxSelected>>", on_preset_command_selected)

    def send(self, data, log=True):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((host, port))
                s.sendall(data.encode() + b"\r\n")
                response = s.recv(1024)

                if log:
                    self.log(f"Sent: {data} - Received: {response.decode()}")
                return response.decode()
            except Exception as e:
                if log:
                    self.log(f"Error sending data: {e}")
                return None

    def send_audio(self):
        window = tk.Toplevel(self.master)
        window.title("Audio Recorder")

        fs = 44100
        duration = 5
        ttk.Label(window, text=f"Recording ({duration} seconds)...").pack()

        def record_audio():
            recording = sd.rec(int(duration * fs),
                               samplerate=fs, channels=2, dtype=np.int16)
            sd.wait()

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.sendall(b"AT+SEND=0,0,")
                s.sendall(recording.tobytes())
                s.sendall(b"\r\n")
                self.log(f"Sent audio data.")

            window.destroy()

        threading.Thread(target=record_audio).start()

    def log(self, message):
        self.logger.config(state=tk.NORMAL)
        self.logger.insert(
            tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        self.logger.config(state=tk.DISABLED)
        self.logger.see(tk.END)

    def clear_log(self):
        self.logger.config(state=tk.NORMAL)
        self.logger.delete("1.0", tk.END)
        self.logger.config(state=tk.DISABLED)

    def on_closing(self):
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
