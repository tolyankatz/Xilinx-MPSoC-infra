# QA Lab - שאלות ותשובות

**שאלה 1:** איך מוגדרת סביבת המעבדה (QA Lab) בפרויקט ומה הרכיבים הפיזיים הנדרשים?

**תשובה:** סביבת המעבדה מוגדרת ב-`test_host/config.yaml` תחת `hardware` וכוללת:
- **Serial Console** - חיבור USB-to-Serial (`/dev/ttyUSB0`, 115200 baud)
- **Network** - קונפיגורציה עבור Ethernet testing (target IP: 192.168.1.100, test host IP: 192.168.1.10)
- **Power Control** - בקרת חשמל דרך smart plug או relay board (IP: 192.168.1.200)
- **JTAG** - כבל Digilent HS2 או Xilinx platform cable לפעולות recovery
הרכיבים הפיזיים כוללים ZCU102 boards, controllable power outlets, JTAG cables, ו-Test Host machine עם גישה לרשת ול-NFS/Artifactory.

**שאלה 2:** איך מוגדרת קונפיגורציית הרשת במעבדה?

**תשובה:** קונפיגורציית הרשת מוגדרת תחת `hardware.network`:
- Target IP: 192.168.1.100 (IP סטטי של ZCU102)
- Test Host IP: 192.168.1.10
- Subnet Mask: 255.255.255.0
- Gateway: 192.168.1.1
- Interface: eth0
הקונפיגורציה מאפשרת בדיקות connectivity, performance ו-network recovery.

**שאלה 3:** איך מוגדר ומנוהל power control במעבדה?

**תשובה:** Power control מוגדר תחת `hardware.power`:
- Controller Type: smart_plug (או relay_board, manual)
- Device ID: zcu102_board_1
- IP Address: 192.168.1.200 (עבור network-controlled outlets)
- Cycle Delay: 5 שניות בין כיבוי להדלקה
זה מאפשר power cycling אוטומטי לפני בדיקות ו-recovery מכישלונים.

**שאלה 4:** איך מוגדרת קונפיגורציית JTAG במעבדה?

**תשובה:** JTAG מוגדר תחת `hardware.jtag`:
- Cable Type: digilent_hs2 (או xilinx platform cable)
- Device Part: xczu9eg (ZCU102 FPGA)
- Chain Position: 1
- Vivado Path: /opt/Xilinx/Vivado/2023.1/bin/vivado
זה מאפשר firmware flashing ו-recovery operations.

**שאלה 5:** מה הדרישות מ-Test Host machine במעבדה?

**תשובה:** Test Host דורש:
- מערכת הפעלה Linux עם Python 3.x
- גישת רשת ל-ZCU102 boards ו-power controllers
- חיבורי USB לserial adapters
- גישה ל-NFS/Artifactory לartifacts
- JTAG drivers ו-Vivado tools
- Docker support לcontainerized testing
- SSH access מ-Jenkins controller

**שאלה 6:** איך מתבצע setup של serial communication במעבדה?

**תשובה:** Serial communication מוגדר תחת `hardware.serial`:
- Port: /dev/ttyUSB0 (USB-to-Serial adapter)
- Baud Rate: 115200
- Timeout: 10 שניות
- Read Timeout: 1 שנייה
נדרש USB-to-Serial adapter איכותי עם drivers יציבים ב-Linux.

**שאלה 7:** איך מנוהלים test fixtures וחומרת עזר במעבדה?

**תשובה:** Test fixtures כוללים:
- GPIO loopback connectors לבדיקות GPIO
- I2C/SPI test boards עם peripherals ידועים
- Network cables ו-switches לbandwidth testing
- Power measurement tools לcurrent monitoring
- Temperature sensors לthermal testing
- Oscilloscopes לsignal integrity validation

**שאלה 8:** איך מתבצע ניהול artifacts ו-storage במעבדה?

**תשובה:** Artifacts מנוהלים דרך:
- NFS mount ל-/mnt/nfs_artifacts עם BSP builds
- Local storage ל-test results ו-logs
- Backup ל-cloud storage (S3/Azure)
- Retention policy של 30 יום לartifacts
- Checksum validation לכל artifact
- Version tracking עם build IDs

**שאלה 9:** איך מתבצע monitoring ו-alerting במעבדה?

**תשובה:** Monitoring כולל:
- Hardware health monitoring (temperature, power)
- Network connectivity checks
- Test Host resource monitoring (CPU, memory, disk)
- JTAG cable status monitoring
- Automated alerts ל-Slack/email על כישלונים
- Dashboard ב-Grafana עם real-time metrics

**שאלה 10:** איך מתבצע maintenance ו-troubleshooting במעבדה?

**תשובה:** Maintenance כולל:
- בדיקות תקופתיות של חיבורים פיזיים
- עדכון drivers ו-firmware של test equipment
- ניקוי ו-defragmentation של storage
- בדיקת power supply stability
- Calibration של measurement tools
- Documentation של known issues ו-workarounds
- Backup ו-restore procedures לקונפיגורציות
