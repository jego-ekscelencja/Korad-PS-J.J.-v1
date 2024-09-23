import sys
import time
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, \
    QComboBox, QWidget, QDial, QLCDNumber, QFrame, QGroupBox, QLineEdit, QRadioButton, QButtonGroup
from PyQt5.QtCore import QTimer
import pyqtgraph as pg  # Importujemy PyQtGraph do wykresów


class KoradController(QMainWindow):
    def __init__(self):
        super().__init__()

        self.serial_connection = None
        self.voltage_value = 0.00  # Początkowa wartość napięcia
        self.current_value = 0.000  # Początkowa wartość prądu

        # Listy do przechowywania danych do wykresów
        self.voltage_data = []
        self.current_data = []
        self.time_data = []
        self.start_time = time.time()

        self.init_ui()

    def init_ui(self):
        # Główne okno
        self.setWindowTitle('KORAD PS Control J.J.')

        # Główna siatka layoutu
        main_layout = QVBoxLayout()

        # Lista rozwijaną z portami COM
        self.com_ports = QComboBox()
        self.refresh_ports()

        # Przycisk do połączenia z wybranym portem COM
        connect_button = QPushButton('Połącz')
        connect_button.clicked.connect(self.connect_serial)

        # Przycisk do rozłączenia z portem COM
        disconnect_button = QPushButton('Rozłącz')
        disconnect_button.clicked.connect(self.disconnect_serial)

        # Przycisk Autoconnect
        autoconnect_button = QPushButton('Autoconnect')
        autoconnect_button.clicked.connect(self.autoconnect)

        # Etykieta statusu połączenia
        self.status_label = QLabel('Status: Niepołączony')

        # Layout do portów
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel('Port:'))
        port_layout.addWidget(self.com_ports)
        port_layout.addWidget(connect_button)
        port_layout.addWidget(disconnect_button)
        port_layout.addWidget(autoconnect_button)
        main_layout.addLayout(port_layout)

        # Layout do statusu
        status_layout = QHBoxLayout()  # Użyj HBoxLayout dla mniejszej przestrzeni
        status_layout.addWidget(self.status_label)
        main_layout.addLayout(status_layout)

        # Separator poziomy
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Layout dla sekcji regulacji napięcia i prądu
        split_layout = QHBoxLayout()

        # Sekcja napięcia (lewa strona)
        voltage_layout = QVBoxLayout()

        # Duży wyświetlacz napięcia
        self.voltage_display = QLCDNumber()
        self.voltage_display.setDigitCount(5)  # Wyświetlacz do 31.00 V
        self.voltage_display.setSegmentStyle(QLCDNumber.Flat)
        self.voltage_display.display(self.voltage_value)  # Początkowa wartość
        self.voltage_display.setStyleSheet("border: 1px solid black; color: green; background: black;")
        self.voltage_display.setFixedHeight(100)  # Powiększony wyświetlacz
        voltage_layout.addWidget(QLabel('Napięcie [V]:'))
        voltage_layout.addWidget(self.voltage_display)

        # Pole do ręcznego wpisania napięcia
        voltage_input_layout = QHBoxLayout()
        self.voltage_input = QLineEdit()
        self.voltage_input.setPlaceholderText('Napięcie')
        self.voltage_input.returnPressed.connect(self.set_voltage_from_input)  # Zatwierdzanie ENTEREM
        voltage_set_button = QPushButton('Ustaw')
        voltage_set_button.clicked.connect(self.set_voltage_from_input)  # Przycisk Ustaw
        voltage_input_layout.addWidget(self.voltage_input)
        voltage_input_layout.addWidget(voltage_set_button)
        voltage_layout.addLayout(voltage_input_layout)

        # Layout dla regulacji napięcia w ramkach
        voltage_control_layout = QHBoxLayout()

        # Grupa 1: Pokrętło jednostek napięcia i przyciski +1V, -1V
        voltage_unit_group = QGroupBox("Jednostki napięcia [V]")
        voltage_unit_layout = QVBoxLayout()

        # Pokrętło do zmiany wartości napięcia (część całkowita)
        self.voltage_dial_volts = QDial()
        self.voltage_dial_volts.setRange(0, 31)  # Zakres 0 do 31 voltów
        self.voltage_dial_volts.setNotchesVisible(True)
        self.voltage_dial_volts.valueChanged.connect(self.update_voltage_display)
        voltage_unit_layout.addWidget(self.voltage_dial_volts)

        # Przyciski +1V i -1V
        voltage_plus_1v = QPushButton('+ 1 V')
        voltage_plus_1v.clicked.connect(self.increment_voltage_1v)
        voltage_unit_layout.addWidget(voltage_plus_1v)

        voltage_minus_1v = QPushButton('- 1 V')
        voltage_minus_1v.clicked.connect(self.decrement_voltage_1v)
        voltage_unit_layout.addWidget(voltage_minus_1v)

        voltage_unit_group.setLayout(voltage_unit_layout)
        voltage_control_layout.addWidget(voltage_unit_group)

        # Grupa 2: Pokrętło setnych części napięcia i przyciski +0.1V, -0.1V, +0.01V, -0.01V
        voltage_fraction_group = QGroupBox("[mV]")
        voltage_fraction_layout = QVBoxLayout()

        # Pokrętło do zmiany wartości napięcia (część setna)
        self.voltage_dial_fraction = QDial()
        self.voltage_dial_fraction.setRange(0, 99)  # Zakres 0.00 do 0.99V
        self.voltage_dial_fraction.setNotchesVisible(True)
        self.voltage_dial_fraction.valueChanged.connect(self.update_voltage_display)
        voltage_fraction_layout.addWidget(self.voltage_dial_fraction)

        # GridLayout dla przycisków +0.1V, -0.1V, +0.01V, -0.01V
        voltage_buttons_grid = QGridLayout()

        self.voltage_plus_01v = QPushButton('+ 0.1 V')
        self.voltage_plus_01v.clicked.connect(self.increment_voltage_01v)
        voltage_buttons_grid.addWidget(self.voltage_plus_01v, 0, 0)

        self.voltage_minus_01v = QPushButton('- 0.1 V')
        self.voltage_minus_01v.clicked.connect(self.decrement_voltage_01v)
        voltage_buttons_grid.addWidget(self.voltage_minus_01v, 1, 0)

        self.voltage_plus_001v = QPushButton('+ 0.01 V')
        self.voltage_plus_001v.clicked.connect(self.increment_voltage_001v)
        voltage_buttons_grid.addWidget(self.voltage_plus_001v, 0, 1)

        self.voltage_minus_001v = QPushButton('- 0.01 V')
        self.voltage_minus_001v.clicked.connect(self.decrement_voltage_001v)
        voltage_buttons_grid.addWidget(self.voltage_minus_001v, 1, 1)

        voltage_fraction_layout.addLayout(voltage_buttons_grid)
        voltage_fraction_group.setLayout(voltage_fraction_layout)

        voltage_control_layout.addWidget(voltage_fraction_group)
        voltage_layout.addLayout(voltage_control_layout)

        # Sekcja prądu (prawa strona)
        current_layout = QVBoxLayout()

        # Duży wyświetlacz prądu
        self.current_display = QLCDNumber()
        self.current_display.setDigitCount(6)  # Wyświetlacz do 5.100 A
        self.current_display.setSegmentStyle(QLCDNumber.Flat)
        self.current_display.display(self.current_value)  # Początkowa wartość
        self.current_display.setStyleSheet("border: 1px solid black; color: green; background: black;")
        self.current_display.setFixedHeight(100)  # Powiększony wyświetlacz
        current_layout.addWidget(QLabel('Prąd [A]:'))
        current_layout.addWidget(self.current_display)

        # Pole do ręcznego wpisania prądu
        current_input_layout = QHBoxLayout()
        self.current_input = QLineEdit()
        self.current_input.setPlaceholderText('Prąd')
        self.current_input.returnPressed.connect(self.set_current_from_input)  # Zatwierdzanie ENTEREM
        current_set_button = QPushButton('Ustaw')
        current_set_button.clicked.connect(self.set_current_from_input)  # Przycisk Ustaw
        current_input_layout.addWidget(self.current_input)
        current_input_layout.addWidget(current_set_button)
        current_layout.addLayout(current_input_layout)

        # Layout dla regulacji prądu w ramkach
        current_control_layout = QHBoxLayout()

        # Grupa 1: Pokrętło jednostek prądu i przyciski +1A, -1A
        current_unit_group = QGroupBox("Jednostki prądu [A]")
        current_unit_layout = QVBoxLayout()

        # Pokrętło do zmiany wartości prądu (część całkowita)
        self.current_dial_amperes = QDial()
        self.current_dial_amperes.setRange(0, 5)  # Zakres 0 do 5 amperów
        self.current_dial_amperes.setNotchesVisible(True)
        self.current_dial_amperes.valueChanged.connect(self.update_current_display)
        current_unit_layout.addWidget(self.current_dial_amperes)

        # Przyciski +1A i -1A
        current_plus_1a = QPushButton('+ 1 A')
        current_plus_1a.clicked.connect(self.increment_current_1a)
        current_unit_layout.addWidget(current_plus_1a)

        current_minus_1a = QPushButton('- 1 A')
        current_minus_1a.clicked.connect(self.decrement_current_1a)
        current_unit_layout.addWidget(current_minus_1a)

        current_unit_group.setLayout(current_unit_layout)
        current_control_layout.addWidget(current_unit_group)

        # Grupa 2: Pokrętło dziesiętnych i setnych części prądu oraz przyciski +0.1A, -0.1A, +0.01A, -0.01A, +0.001A, -0.001A
        self.current_fraction_group = QGroupBox("[mA]")
        self.current_fraction_layout = QVBoxLayout()

        # Pokrętło do zmiany wartości prądu (część setna)
        self.current_dial_fraction = QDial()
        self.current_dial_fraction.setRange(0, 999)  # Zakres 0.000 do 0.999A
        self.current_dial_fraction.setNotchesVisible(True)
        self.current_dial_fraction.valueChanged.connect(self.update_current_display)
        self.current_fraction_layout.addWidget(self.current_dial_fraction)

        # GridLayout dla przycisków +0.1A, -0.1A, +0.01A, -0.01A, +0.001A, -0.001A
        self.current_buttons_grid = QGridLayout()

        self.current_plus_01a = QPushButton('+ 100 mA')
        self.current_plus_01a.clicked.connect(self.increment_current_01a)
        self.current_buttons_grid.addWidget(self.current_plus_01a, 0, 0)

        self.current_minus_01a = QPushButton('- 100 mA')
        self.current_minus_01a.clicked.connect(self.decrement_current_01a)
        self.current_buttons_grid.addWidget(self.current_minus_01a, 1, 0)

        self.current_plus_001a = QPushButton('+ 10 mA')
        self.current_plus_001a.clicked.connect(self.increment_current_001a)
        self.current_buttons_grid.addWidget(self.current_plus_001a, 0, 1)

        self.current_minus_001a = QPushButton('- 10 mA')
        self.current_minus_001a.clicked.connect(self.decrement_current_001a)
        self.current_buttons_grid.addWidget(self.current_minus_001a, 1, 1)

        self.current_plus_0001a = QPushButton('+ 1 mA')
        self.current_plus_0001a.clicked.connect(self.increment_current_0001a)
        self.current_buttons_grid.addWidget(self.current_plus_0001a, 0, 2)

        self.current_minus_0001a = QPushButton('- 1 mA')
        self.current_minus_0001a.clicked.connect(self.decrement_current_0001a)
        self.current_buttons_grid.addWidget(self.current_minus_0001a, 1, 2)

        self.current_fraction_layout.addLayout(self.current_buttons_grid)

        self.current_fraction_group.setLayout(self.current_fraction_layout)

        current_control_layout.addWidget(self.current_fraction_group)
        current_layout.addLayout(current_control_layout)

        # Separator pionowy pomiędzy napięciem i prądem
        vertical_separator = QFrame()
        vertical_separator.setFrameShape(QFrame.VLine)
        vertical_separator.setFrameShadow(QFrame.Sunken)

        # Dodanie layoutów sekcji napięcia i prądu do głównego layoutu
        split_layout.addLayout(voltage_layout)
        split_layout.addWidget(vertical_separator)
        split_layout.addLayout(current_layout)

        # Dodanie podzielonego layoutu do głównego layoutu
        main_layout.addLayout(split_layout)

        # Separator poziomy przed RadioButtons i przyciskami
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator2)

        # Layout dla RadioButtons i przycisków Załącz/Wyłącz z pionowym separatorem
        controls_layout = QHBoxLayout()

        # Grupa: Sterowanie - załączanie i wyłączanie wyjścia
        control_group = QGroupBox("Sterowanie")
        control_group_layout = QVBoxLayout()
        enable_output_button = QPushButton("Załącz")
        enable_output_button.clicked.connect(self.enable_output)
        disable_output_button = QPushButton("Wyłącz")
        disable_output_button.clicked.connect(self.disable_output)
        control_group_layout.addWidget(enable_output_button)
        control_group_layout.addWidget(disable_output_button)
        control_group.setLayout(control_group_layout)

        # Grupa: Jednostki - RadioButtons
        unit_group = QGroupBox("Jednostki")
        unit_group_layout = QVBoxLayout()
        self.radio_mA = QRadioButton("mA")
        self.radio_001A = QRadioButton("0.001A")
        self.radio_mA.setChecked(True)  # Domyślnie zaznaczone mA

        # Dodaj RadioButtons do grupy, aby były wzajemnie wykluczające się
        radio_group = QButtonGroup(self)
        radio_group.addButton(self.radio_mA)
        radio_group.addButton(self.radio_001A)

        self.radio_mA.toggled.connect(self.update_current_button_labels)

        unit_group_layout.addWidget(self.radio_mA)
        unit_group_layout.addWidget(self.radio_001A)
        unit_group.setLayout(unit_group_layout)

        # Dodanie layoutów do controls_layout z separatorem pionowym
        controls_layout.addWidget(control_group)
        controls_layout.addWidget(unit_group)

        main_layout.addLayout(controls_layout)

        # Separator poziomy przed sekcją odczytu danych
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator3)

        # Nowa sekcja dla odczytanych wartości napięcia i prądu
        readout_layout = QHBoxLayout()

        # Wyświetlacz napięcia odczytanego
        voltage_readout_layout = QVBoxLayout()
        self.voltage_readout_display = QLCDNumber()
        self.voltage_readout_display.setDigitCount(5)
        self.voltage_readout_display.setSegmentStyle(QLCDNumber.Flat)
        self.voltage_readout_display.setStyleSheet("border: 1px solid black; color: #FFBF00; background: black;")
        self.voltage_readout_display.setFixedHeight(100)
        voltage_readout_layout.addWidget(QLabel('Napięcie odczytane [V]:'))
        voltage_readout_layout.addWidget(self.voltage_readout_display)

        # Wyświetlacz prądu odczytanego
        current_readout_layout = QVBoxLayout()
        self.current_readout_display = QLCDNumber()
        self.current_readout_display.setDigitCount(6)
        self.current_readout_display.setSegmentStyle(QLCDNumber.Flat)
        self.current_readout_display.setStyleSheet("border: 1px solid black; color: #FFBF00; background: black;")
        self.current_readout_display.setFixedHeight(100)
        current_readout_layout.addWidget(QLabel('Prąd odczytany [A]:'))
        current_readout_layout.addWidget(self.current_readout_display)

        # Dodanie wyświetlaczy do layoutu
        readout_layout.addLayout(voltage_readout_layout)
        readout_layout.addLayout(current_readout_layout)

        # Dodanie nowej sekcji do głównego layoutu
        main_layout.addLayout(readout_layout)

        # **Dodanie wykresów poniżej wyświetlaczy**

        # Tworzenie wykresów
        plots_layout = QHBoxLayout()

        # Wykres napięcia
        self.voltage_plot_widget = pg.PlotWidget(title='Wykres Napięcia')
        self.voltage_plot_widget.setLabel('left', 'Napięcie [V]')
        self.voltage_plot_widget.setLabel('bottom', 'Czas [s]')
        self.voltage_curve = self.voltage_plot_widget.plot(pen='g')  # Zielony wykres
        plots_layout.addWidget(self.voltage_plot_widget)

        # Wykres prądu
        self.current_plot_widget = pg.PlotWidget(title='Wykres Prądu')
        self.current_plot_widget.setLabel('left', 'Prąd [A]')
        self.current_plot_widget.setLabel('bottom', 'Czas [s]')
        self.current_curve = self.current_plot_widget.plot(pen='r')  # Czerwony wykres
        plots_layout.addWidget(self.current_plot_widget)

        # Dodanie wykresów do głównego layoutu
        main_layout.addLayout(plots_layout)

        # Timer do odczytu napięcia i prądu co 300ms
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.read_voltage_and_current)
        self.readout_timer.start(300)

        # Ustawienie głównego widgetu
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    # Reszta metod pozostaje bez zmian...

    def refresh_ports(self):
        """Odśwież listę dostępnych portów COM."""
        ports = serial.tools.list_ports.comports()
        self.com_ports.clear()
        for port in ports:
            self.com_ports.addItem(port.device)

    def connect_serial(self):
        """Połącz się z wybranym portem COM i pobierz aktualne ustawienia zasilacza."""
        port = self.com_ports.currentText()
        try:
            self.serial_connection = serial.Serial(port, baudrate=9600, timeout=2)
            self.status_label.setText(f'Status: Połączono z {port}')
            print(f'Połączono z {port}')

            # Pobierz ustawienia zasilacza po połączeniu
            self.fetch_voltage_current_settings()
        except serial.SerialException as e:
            self.status_label.setText(f'Status: Błąd połączenia z {port}')
            print(f'Błąd połączenia z {port}: {e}')

    def disconnect_serial(self):
        """Rozłącz się z zasilaczem."""
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
            self.status_label.setText('Status: Rozłączono')
            print('Rozłączono od zasilacza.')

    def autoconnect(self):
        """Autoconnect - wyszukiwanie zasilacza Korad i pobranie ustawień."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            try:
                ser = serial.Serial(port.device, baudrate=9600, timeout=2)
                ser.write(b'*IDN?\n')
                response = ser.readline().decode().strip()
                if 'KORAD' in response:
                    self.serial_connection = ser
                    self.status_label.setText(f'Połączono z portem {port.device}, urządzenie: {response}')
                    print(f'Połączono z portem {port.device}, urządzenie: {response}')

                    # Ustaw port COM w rozwijanej liście jako wybrany
                    self.set_selected_com_port(port.device)

                    # Pobierz ustawienia zasilacza po połączeniu
                    self.fetch_voltage_current_settings()
                    return
                ser.close()
            except Exception as e:
                print(f'Błąd autoconnect: {e}')
        self.status_label.setText('Nie znaleziono zasilacza KORAD')

    def set_selected_com_port(self, port_name):
        """Ustaw wskazany port COM jako wybrany w rozwijanej liście."""
        index = self.com_ports.findText(port_name)
        if index >= 0:
            self.com_ports.setCurrentIndex(index)

    def fetch_voltage_current_settings(self):
        """Pobierz obecne ustawienia napięcia i prądu z zasilacza i zaktualizuj interfejs."""
        try:
            # Pobierz ustawione napięcie
            self.serial_connection.write(b'VSET1?\n')  # Użycie VSET1?
            voltage_response = self.serial_connection.readline().decode().strip()
            voltage = float(voltage_response)

            # Pobierz ustawiony prąd
            self.serial_connection.write(b'ISET1?\n')  # Użycie ISET1?
            current_response = self.serial_connection.readline().decode().strip()
            current = float(current_response)

            # Aktualizuj wyświetlacze i pokrętła
            self.set_voltage(voltage)
            self.set_current(current)

            print(f'Pobrano ustawione napięcie: {voltage:.2f} V, prąd: {current:.3f} A')
        except Exception as e:
            print(f'Błąd pobierania ustawień: {e}')

    def read_voltage_and_current(self):
        """Odczytaj napięcie i prąd z zasilacza co 300ms."""
        try:
            # Pobierz odczyt napięcia
            self.serial_connection.write(b'VOUT1?\n')
            voltage_response = self.serial_connection.readline().decode().strip()
            voltage = float(voltage_response)

            # Pobierz odczyt prądu
            self.serial_connection.write(b'IOUT1?\n')
            current_response = self.serial_connection.readline().decode().strip()
            current = float(current_response)

            # Zaktualizuj wyświetlacze odczytanych wartości
            self.voltage_readout_display.display(f"{voltage:.2f}")
            self.current_readout_display.display(f"{current:.3f}")

            # Dodaj nowe dane do list
            current_time = time.time() - self.start_time
            self.time_data.append(current_time)
            self.voltage_data.append(voltage)
            self.current_data.append(current)

            # Aktualizuj wykresy
            self.voltage_curve.setData(self.time_data, self.voltage_data)
            self.current_curve.setData(self.time_data, self.current_data)

            print(f'Odczytane napięcie: {voltage:.2f} V, prąd: {current:.3f} A')
        except Exception as e:
            print(f'Błąd odczytu napięcia i prądu: {e}')

    def set_voltage(self, voltage):
        """Ustaw napięcie w pamięci i zaktualizuj interfejs."""
        self.voltage_value = voltage
        volts = int(voltage)
        fraction = int((voltage - volts) * 100)
        self.voltage_dial_volts.setValue(volts)
        self.voltage_dial_fraction.setValue(fraction)
        self.voltage_display.display(f"{voltage:.2f}")

    def set_current(self, current):
        """Ustaw prąd w pamięci i zaktualizuj interfejs."""
        self.current_value = current
        amperes = int(current)
        fraction = int((current - amperes) * 1000)
        self.current_dial_amperes.setValue(amperes)
        self.current_dial_fraction.setValue(fraction)
        self.current_display.display(f"{current:.3f}")

    def set_voltage_from_input(self):
        """Ustaw napięcie z wpisanego pola."""
        try:
            # Akceptacja zarówno kropki, jak i przecinka jako separatora dziesiętnego
            voltage_input = self.voltage_input.text().replace(',', '.')
            voltage = float(voltage_input)
            if 0 <= voltage <= 31.0:
                self.set_voltage(voltage)
                if self.serial_connection:
                    self.serial_connection.write(f'VSET1:{voltage:.2f}\n'.encode())
                    print(f'Ustawiono napięcie: {voltage:.2f}V')
        except ValueError:
            print('Błędna wartość napięcia!')

    def set_current_from_input(self):
        """Ustaw prąd z wpisanego pola."""
        try:
            # Akceptacja zarówno kropki, jak i przecinka jako separatora dziesiętnego
            current_input = self.current_input.text().replace(',', '.')
            current = float(current_input)
            if 0 <= current <= 5.1:
                self.set_current(current)
                if self.serial_connection:
                    self.serial_connection.write(f'ISET1:{current:.3f}\n'.encode())
                    print(f'Ustawiono prąd: {current:.3f}A')
        except ValueError:
            print('Błędna wartość prądu!')

    def update_voltage_display(self):
        """Aktualizuj wyświetlacz napięcia na podstawie pokręteł."""
        volts = self.voltage_dial_volts.value()  # Wartość z pokrętła voltów
        fraction = self.voltage_dial_fraction.value()  # Wartość z pokrętła setnych
        voltage = volts + fraction / 100.0  # Oblicz pełne napięcie
        self.voltage_value = voltage
        self.voltage_display.display(f"{voltage:.2f}")  # Wyświetl wynik

        # Wyślij polecenie ustawienia napięcia do zasilacza
        if self.serial_connection:
            try:
                self.serial_connection.write(f'VSET1:{voltage:.2f}\n'.encode())
                print(f'Ustawiono napięcie: {voltage:.2f}V')
            except Exception as e:
                print(f'Błąd wysyłania komendy ustawienia napięcia: {e}')

    def update_current_display(self):
        """Aktualizuj wyświetlacz prądu na podstawie pokręteł."""
        amperes = self.current_dial_amperes.value()  # Wartość z pokrętła amperów
        fraction = self.current_dial_fraction.value()  # Wartość z pokrętła setnych i tysięcznych
        current = amperes + fraction / 1000.0  # Oblicz pełny prąd
        self.current_value = current
        self.current_display.display(f"{current:.3f}")  # Wyświetl wynik

        # Wyślij polecenie ustawienia prądu do zasilacza
        if self.serial_connection:
            try:
                self.serial_connection.write(f'ISET1:{current:.3f}\n'.encode())
                print(f'Ustawiono prąd: {current:.3f}A')
            except Exception as e:
                print(f'Błąd wysyłania komendy ustawienia prądu: {e}')

    def increment_voltage_1v(self):
        """Zwiększ napięcie o 1 V."""
        if self.voltage_value + 1.0 <= 31.0:
            self.voltage_dial_volts.setValue(self.voltage_dial_volts.value() + 1)

    def decrement_voltage_1v(self):
        """Zmniejsz napięcie o 1 V."""
        if self.voltage_value - 1.0 >= 0.0:
            self.voltage_dial_volts.setValue(self.voltage_dial_volts.value() - 1)

    def increment_voltage_01v(self):
        """Zwiększ napięcie o 0.1 V."""
        if self.voltage_value + 0.1 <= 31.0:
            self.voltage_dial_fraction.setValue(self.voltage_dial_fraction.value() + 10)

    def decrement_voltage_01v(self):
        """Zmniejsz napięcie o 0.1 V."""
        if self.voltage_value - 0.1 >= 0.0:
            self.voltage_dial_fraction.setValue(self.voltage_dial_fraction.value() - 10)

    def increment_voltage_001v(self):
        """Zwiększ napięcie o 0.01 V."""
        if self.voltage_value + 0.01 <= 31.0:
            self.voltage_dial_fraction.setValue(self.voltage_dial_fraction.value() + 1)

    def decrement_voltage_001v(self):
        """Zmniejsz napięcie o 0.01 V."""
        if self.voltage_value - 0.01 >= 0.0:
            self.voltage_dial_fraction.setValue(self.voltage_dial_fraction.value() - 1)

    def increment_current_1a(self):
        """Zwiększ prąd o 1 A."""
        if self.current_value + 1.0 <= 5.1:
            self.current_dial_amperes.setValue(self.current_dial_amperes.value() + 1)

    def decrement_current_1a(self):
        """Zmniejsz prąd o 1 A."""
        if self.current_value - 1.0 >= 0.0:
            self.current_dial_amperes.setValue(self.current_dial_amperes.value() - 1)

    def increment_current_01a(self):
        """Zwiększ prąd o 0.1 A."""
        if self.current_value + 0.1 <= 5.1:
            self.current_dial_amperes.setValue(self.current_dial_amperes.value() + 1)

    def decrement_current_01a(self):
        """Zmniejsz prąd o 0.1 A."""
        if self.current_value - 0.1 >= 0.0:
            self.current_dial_amperes.setValue(self.current_dial_amperes.value() - 1)

    def increment_current_001a(self):
        """Zwiększ prąd o 0.01 A."""
        if self.current_value + 0.01 <= 5.1:
            self.current_dial_fraction.setValue(self.current_dial_fraction.value() + 10)

    def decrement_current_001a(self):
        """Zmniejsz prąd o 0.01 A."""
        if self.current_value - 0.01 >= 0.0:
            self.current_dial_fraction.setValue(self.current_dial_fraction.value() - 10)

    def increment_current_0001a(self):
        """Zwiększ prąd o 0.001 A."""
        if self.current_value + 0.001 <= 5.1:
            self.current_dial_fraction.setValue(self.current_dial_fraction.value() + 1)

    def decrement_current_0001a(self):
        """Zmniejsz prąd o 0.001 A."""
        if self.current_value - 0.001 >= 0.0:
            self.current_dial_fraction.setValue(self.current_dial_fraction.value() - 1)

    def enable_output(self):
        """Załącz wyjście zasilacza."""
        if self.serial_connection:
            self.serial_connection.write(b'OUT1\n')
            print('Wyjście załączone')

    def disable_output(self):
        """Wyłącz wyjście zasilacza."""
        if self.serial_connection:
            self.serial_connection.write(b'OUT0\n')
            print('Wyjście wyłączone')

    def update_current_button_labels(self):
        """Zmieniaj dynamicznie etykiety przycisków w zależności od wybranego RadioButton."""
        if self.radio_mA.isChecked():
            self.current_fraction_group.setTitle("[mA]")
            self.current_plus_01a.setText('+ 100 mA')
            self.current_minus_01a.setText('- 100 mA')
            self.current_plus_001a.setText('+ 10 mA')
            self.current_minus_001a.setText('- 10 mA')
            self.current_plus_0001a.setText('+ 1 mA')
            self.current_minus_0001a.setText('- 1 mA')
        else:
            self.current_fraction_group.setTitle("[A]")
            self.current_plus_01a.setText('+ 0.1 A')
            self.current_minus_01a.setText('- 0.1 A')
            self.current_plus_001a.setText('+ 0.01 A')
            self.current_minus_001a.setText('- 0.01 A')
            self.current_plus_0001a.setText('+ 0.001 A')
            self.current_minus_0001a.setText('- 0.001 A')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = KoradController()
    window.show()
    sys.exit(app.exec_())
