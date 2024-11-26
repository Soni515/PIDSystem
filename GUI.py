import tkinter as tk # Untuk membuat GUI
from tkinter import ttk # Untuk membuat widget seperti combobox
import serial.tools.list_ports # Untuk mendeteksi Serial Ports yang ada di Komputer
import threading # Untuk membaca data melalu serial port
import time # Untuk hal terkait waktu
import serial # Untuk Komunikasi serial
import numpy as np # Untuk memanipulasi data didalam array
from matplotlib.figure import Figure # Untuk membuat grafik
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # Untuk menghubungkan grafik dengan GUI

# Membuat window utama
window = tk.Tk()

# Title
window.title("GUI Praktik Sistem Kendali - Motor Driver")

# Fullscreen
window.attributes("-fullscreen", True)

# Binding langsung keluar full screen dengan Escape
window.bind("<Escape>", lambda event: window.attributes("-fullscreen", False) or window.geometry("1920x1080"))

# Serial port object
ser = None
data_thread = None

# Data lists
times = [] # Menyimpan data waktu yang diterima dari Microcontroller
rpms = [] # Menyimpan data RPM
setpoints = [] # Menyimpan data Set Point
transient_calculated = False # Status apakah parameter transient telah dihitung atau belum

# Menambahkan Dropdown box untuk Serial Port
def refresh_ports():
    ports = list(serial.tools.list_ports.comports()) # Untuk mendapatkan daftar port
    portList = [port.device for port in ports] # Untuk mendapatkan nama Serial Port yang terhubung
    dropdown['values'] = portList # Untuk menetapkann yang keluar di dalam dropdown

def connect_serial():
    global ser, data_thread # Mengaksees Variable diluar fungsi (ser, data_thread)
    port = dropdown.get() # Untuk mengambil nilai yang dipilih di Dropdown
    if port: # Jika nilai port valid
        try:
            ser = serial.Serial(port, 9600, timeout=1) #
            print(f"Connected to {port}")
            # Mulai thread untuk membaca data serial
            data_thread = threading.Thread(target=read_serial_data) # Untuk menjalankan fungsi tertentu secara paralel
            data_thread.daemon = True # Otomatis berhenti ketika program berhenti
            data_thread.start()
        except Exception as e:
            print(f"Failed to connect to {port}: {e}") # Jika ada kesalahan pada block try, ini akan berjalan

def read_serial_data():
    global ser, times, rpms, setpoints
    while True:
        if ser.in_waiting: # informasi tentang jumlah byte yang tersedia untuk dibaca dari buffer serial
            try:
                line = ser.readline().decode('utf-8').strip() # Fungsi ini membaca satu baris data dari port serial. Baris ini biasanya diakhiri dengan karakter newline
                if line.startswith("DATA:"):
                    line = line[5:]  # Hilangkan prefix "DATA:"
                    # Format data: <time>,<rpm>,<setpoint>
                    parts = line.split(',')
                    if len(parts) == 3:
                        time_value = float(parts[0])
                        rpm_value = float(parts[1])
                        setpoint_value = float(parts[2])
                        # Menambahkan Data di variabel
                        times.append(time_value)
                        rpms.append(rpm_value)
                        setpoints.append(setpoint_value)
                        # Jadwalkan pembaruan plot di thread utama
                        window.after(0, update_plot)
                        # Perbarui nilai RPM di GUI
                        window.after(0, rpmValue.config, {'text': f"{rpm_value:.2f}"})
                        # Hitung parameter transien jika data cukup
                        if len(times) > 2:
                            calculate_transient_parameters()
                    else:
                        print(f"Received data line with incorrect format: {line}")
                else:
                    # Abaikan pesan lain
                    pass
            except Exception as e:
                print(f"Error reading line: {line}, error: {e}")
        else:
            time.sleep(0.01)  # Tidur sebentar untuk menghindari penggunaan CPU berlebih

# Update Plot
def update_plot():
    ax.clear()
    ax.grid(True)
    ax.plot(times, rpms, label='RPM')
    ax.plot(times, setpoints, label='Setpoint')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('RPM')
    ax.legend()
    canvas.draw()

def send_setpoint():
    global ser, transient_calculated
    if ser:
        setpoint = setPointEntry.get()
        direction = directionVar.get()
        if setpoint:
            try:
                setpoint_value = float(setpoint)
                if direction == "Clockwise":
                    command = f"F{setpoint_value}\n"
                else:
                    command = f"R{setpoint_value}\n"
                ser.write(command.encode('utf-8')) # Mengirim perintah ke microcontroller
                print(f"Sent command: {command}")
                # Reset data dan flag saat mengirim setpoint baru
                times.clear()
                rpms.clear()
                setpoints.clear()
                transient_calculated = False
                # Reset parameter transien di GUI
                reset_transient_parameters()
            except ValueError:
                print("Invalid setpoint value")
        else:
            print("Setpoint is empty")
    else:
        print("Serial port is not connected")

def send_pid_parameters():
    global ser
    if ser:
        kp_value = kp_scale.get()
        ki_value = ki_scale.get()
        kd_value = kd_scale.get()
        command = f"PID,{kp_value},{ki_value},{kd_value}\n"
        ser.write(command.encode('utf-8'))
        print(f"Sent PID parameters: kp={kp_value}, ki={ki_value}, kd={kd_value}")
    else:
        print("Serial port is not connected")

def send_stop_command():
    global ser, transient_calculated
    if ser:
        command = "STOP\n"
        ser.write(command.encode('utf-8'))
        print(f"Sent command: {command.strip()}")
        # Reset data dan flag saat motor berhenti
        times.clear()
        rpms.clear()
        setpoints.clear()
        transient_calculated = False
        # Perbarui nilai RPM di GUI menjadi 0
        window.after(0, rpmValue.config, {'text': "0.00"})
        # Reset parameter transien di GUI
        reset_transient_parameters()
    else:
        print("Serial port is not connected")

def calculate_transient_parameters():
    global times, rpms, setpoints
    # Pastikan data cukup untuk perhitungan
    if len(times) < 5:
        return

    # Ambil setpoint terakhir yang bukan nol
    setpoint_values = [sp for sp in setpoints if sp != 0]
    if not setpoint_values:
        return
    setpoint_value = setpoint_values[-1]

    # Konversi list ke array numpy untuk perhitungan yang lebih mudah
    times_array = np.array(times)
    rpms_array = np.array(rpms)

    # Hitung Rise Time (10% ke 90% dari setpoint)
    rise_start = 0.1 * setpoint_value
    rise_end = 0.9 * setpoint_value

    try:
        time_rise_start = times_array[np.where(rpms_array >= rise_start)[0][0]]
        time_rise_end = times_array[np.where(rpms_array >= rise_end)[0][0]]
        rise_time = time_rise_end - time_rise_start
    except IndexError:
        rise_time = 0.0  # Jika tidak ditemukan, set ke 0

    # Hitung Peak Time
    peak_index = np.argmax(rpms_array)
    peak_time = times_array[peak_index]
    peak_value = rpms_array[peak_index]

    # Hitung Overshoot
    overshoot = ((peak_value - setpoint_value) / setpoint_value) * 100

    # Hitung Settling Time (masuk pertama kali dalam ±5% dari setpoint)
    settling_upper = 1.05 * setpoint_value
    settling_lower = 0.95 * setpoint_value
    settling_indices = np.where((rpms_array <= settling_upper) & (rpms_array >= settling_lower))[0]

    if len(settling_indices) > 0:
        settling_time = times_array[settling_indices[0]]  # Ambil waktu pertama kali masuk ke dalam batas
    else:
        settling_time = times_array[-1]

    # Perbarui nilai parameter transien di GUI
    window.after(0, rise_time_value.config, {'text': f"{rise_time:.2f}"})
    window.after(0, peak_time_value.config, {'text': f"{peak_time:.2f}"})
    window.after(0, overshoot_value.config, {'text': f"{overshoot:.2f}"})
    window.after(0, settling_time_value.config, {'text': f"{settling_time:.2f}"})


def reset_transient_parameters():
    window.after(0, rise_time_value.config, {'text': "0.00"})
    window.after(0, peak_time_value.config, {'text': "0.00"})
    window.after(0, overshoot_value.config, {'text': "0.00"})
    window.after(0, settling_time_value.config, {'text': "0.00"})

# Label
label = tk.Label(window, text="Pilih Serial Port:")
label.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

# Connect Button
connectButton = tk.Button(window, text="Connect", command=connect_serial, height=1, width=10, font=("Arial", 7))
connectButton.grid(row=0, column=0, padx=320, pady=10, sticky="nw")

# Stop Button
stopButton = tk.Button(window, text="Stop", command=send_stop_command, height=1, width=10, font=("Arial", 7))
stopButton.place(x=400, y=10)  # Atur posisi tombol sesuai kebutuhan


    # Dropdown untuk memilih serial port
dropdown = ttk.Combobox(window, state='readonly')
dropdown.grid(row=0, column=0, padx=100, pady=10, sticky="nw")

    # Tombol untuk merefresh daftar serial port
refreshButton = tk.Button(window, text="Refresh Ports", command=refresh_ports, height=1, width=10, font=("Arial", 7))
refreshButton.grid(row=0, column=0, padx=250, pady=10, sticky="nw")

refresh_ports()

# Frame untuk Set Point, Putar Maju atau Mundur, dan Pembacaan RPM
frameSet = tk.LabelFrame(window, text="Set Point", padx=10, pady=10)
frameSet.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")

# Label untuk Set Point
setPointLabel = tk.Label(frameSet, text="Set Point (RPM):")
setPointLabel.grid(row=0, column=0, padx=1, pady=5, sticky="w")

# Entry untuk memasukkan angka Set Point
setPointEntry = tk.Entry(frameSet, width=15)
setPointEntry.grid(row=1, column=0, padx=5, pady=5, sticky="w")

    # Tombol untuk merefresh daftar serial port
sendButton = tk.Button(frameSet, text="Send", command=send_setpoint, height=1, width=10, font=("Arial", 7))
sendButton.place(x=110, y=35)

refresh_ports()

# Label untuk Putar Maju atau Mundur
direction = tk.Label(frameSet, text="Direction \n(Clockwise or Counter Clockwise):", justify="left")
direction.grid(row=3, column=0, padx=1, pady=5, sticky="w")

# Pilihan untuk Direction
directionVar = tk.StringVar()
directionVar.set("Clockwise")  # Default value
directionOptions = tk.OptionMenu(frameSet, directionVar, "Clockwise", "Counter Clockwise")
directionOptions.grid(row=4, column=0, padx=1, pady=5, sticky="w")

# Hasil Pembacaan RPM
rpm = tk.Label(frameSet, text="Hasil Pembacaan (RPM): ")
rpm.grid(row=5, column=0, padx=1, pady=5, sticky="w")
rpmValue = tk.Label(frameSet, text="", relief="sunken", width=14, height=1,
                    borderwidth=1, bg="white", highlightbackground="gray")
rpmValue.grid(row=6, column=0, padx=1, pady=5, sticky="w")

# Frame untuk Kontrol PID
pid_frame = tk.LabelFrame(window, text="Kontrol PID", padx=10, pady=10)
pid_frame.grid(row=2, column=0, padx=10, pady=10, sticky="w")

# Slider Kp
kp_label = tk.Label(pid_frame, text="Kp:")
kp_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
kp_scale = tk.Scale(pid_frame, from_=0.0, to=10.0, resolution=0.1, orient=tk.HORIZONTAL, length=140)
kp_scale.set(2.0)
kp_scale.grid(row=0, column=1, padx=5, pady=2)

# Slider Ki
ki_label = tk.Label(pid_frame, text="Ki:")
ki_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
ki_scale = tk.Scale(pid_frame, from_=0.0, to=10.0, resolution=0.1, orient=tk.HORIZONTAL, length=140)
ki_scale.set(1.0)
ki_scale.grid(row=1, column=1, padx=5, pady=2)

# Slider Kd
kd_label = tk.Label(pid_frame, text="Kd:")
kd_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
kd_scale = tk.Scale(pid_frame, from_=0.0, to=10.0, resolution=0.1, orient=tk.HORIZONTAL, length=140)
kd_scale.set(0.2)
kd_scale.grid(row=2, column=1, padx=5, pady=2)

# Send PID Parameter Button
sendPIDButton = tk.Button(pid_frame, text="Send", command=send_pid_parameters, padx=73)
sendPIDButton.grid(row=3, column=0, columnspan=2, pady=5, sticky="w")

# Tambahkan Frame untuk Parameter Transient
transient_frame = tk.LabelFrame(window, text="Parameter Transient", padx=10, pady=10)
transient_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")

# Label untuk Rise Time
rise_time_label = tk.Label(transient_frame, text="Rise Time (s):")
rise_time_label.grid(row=0, column=0, padx=7, pady=5, sticky="w")
rise_time_value = tk.Label(transient_frame, text="0.00")
rise_time_value.grid(row=0, column=1, padx=27, pady=5, sticky="w")

# Label untuk Settling Time
settling_time_label = tk.Label(transient_frame, text="Settling Time (s):")
settling_time_label.grid(row=1, column=0, padx=7, pady=5, sticky="w")
settling_time_value = tk.Label(transient_frame, text="0.00")
settling_time_value.grid(row=1, column=1, padx=27, pady=5, sticky="w")

# Label untuk Overshoot
overshoot_label = tk.Label(transient_frame, text="Overshoot (%):")
overshoot_label.grid(row=2, column=0, padx=7, pady=5, sticky="w")
overshoot_value = tk.Label(transient_frame, text="0.00")
overshoot_value.grid(row=2, column=1, padx=27, pady=5, sticky="w")

# Label untuk Peak Time
peak_time_label = tk.Label(transient_frame, text="Peak Time (s):")
peak_time_label.grid(row=3, column=0, padx=7, pady=5, sticky="w")
peak_time_value = tk.Label(transient_frame, text="0.00")
peak_time_value.grid(row=3, column=1, padx=27, pady=5, sticky="w")

# Frame untuk Plot
plot_frame = tk.Frame(window)
plot_frame.place(x=255, y=57, width=1000, height=600)

# Membuat figure matplotlib
fig = Figure(figsize=(10, 6), dpi=100)
ax = fig.add_subplot(111)
ax.grid(True)

# Menambahkan canvas ke Tkinter
canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.draw()
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Menjalankan loop utama
window.mainloop()