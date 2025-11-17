# Implementation - שאלות ותשובות

**שאלה 1:** מה השפה העיקרית שבה מומש framework הולידציה של ZCU102 ואיך מאורגנים הרכיבים העיקריים?

**תשובה:** framework הולידציה מומש בעיקר ב-Python. הרכיבים העיקריים מאורגנים תחת התיקייה `test_host/` הכוללת:
- `run_tests.py` - הקובץ הראשי לתזמור הבדיקות
- `framework/` - ספריות הליבה לבדיקות
- `hardware_control/` - בקרת חומרה (power, JTAG)
- `reporters/` - דיווח תוצאות (Prometheus, ELK)
- `tests/` - חבילת הבדיקות עצמה
- `requirements.txt` - תלויות Python כולל pytest ותוספים נוספים

**שאלה 2:** איך מומש מנגנון הבקרה על החומרה בפרויקט ומה המטרה של השכבת ההפשטה?

**תשובה:** בקרת החומרה מומשה תחת `test_host/hardware_control/` עם שכבת הפשטה המספקת factory functions כמו `create_power_controller` ו-`create_jtag_controller`. השכבה מסתירה פרטים טכניים של smart plugs, relays וכלי JTAG. כך ה-orchestrator ו-pytest fixtures מתקשרים רק עם ההפשטות, מה שמקל על הרחבה ועל יצירת mock objects לפיתוח. הקונפיגורציה נטענת מ-`config.yaml` תחת `hardware.power` ו-`hardware.jtag`.

**שאלה 3:** איך מומש מנגנון הטעינה והפצת הקונפיגורציה בקוד?

**תשובה:** הקונפיגורציה נטענת דרך `test_config` pytest fixture ב-`test_host/tests/conftest.py`. ה-fixture טוען YAML מ-`test_host/config.yaml` ואז דורס שדות כמו `board_type`, `build_version`, `test_suite`, `skip_hardware` ו-`power_cycle` בהתבסס על אפשרויות command-line. המילון הזה מועבר ל-fixtures ולמחלקות utility כך שכל הרכיבים חולקים קונפיגורציה עקבית.

**שאלה 4:** איך מומש התמיכה ב-mock hardware לפיתוח?

**תשובה:** גם `run_tests.py` וגם `conftest.py` בודקים דגלי קונפיגורציה כמו `development.mock_hardware` (במילון config) ו-`--skip-hardware` (אפשרות pytest CLI). כשמופעל, ה-factories יוצרים mock controllers במקום אמיתיים, ובדיקות מסומנות hardware יכולות להיות מדולגות. זה מאפשר למפתחים להריץ בדיקות בלי חומרת מעבדה תוך שמירה על אותם נתיבי קוד במידת האפשר.

**שאלה 5:** איך מומש הטיפול ב-BSP deployment manifest בקוד?

**תשובה:** הלוגיקה לפרסור BSP deployment manifests נמצאת ב-method `TestOrchestrator.parse_deployment_manifest` ב-`test_host/run_tests.py`. הוא תומך גם בפורמט BSP manifest חדש (עם מפתחות כמו `manifest_version`, `build_info`, `artifacts`) וגם ב-legacy Kubernetes-style manifests. ה-method מאכלס את מילון ה-`config` עם build version, commit hash, board type, artifact repository ו-test plan.

**שאלה 6:** איך מומש הורדת artifacts ו-firmware flashing?

**תשובה:** לאחר פרסור deployment manifest, `_download_artifact` ב-`run_tests.py` משתמש ב-`requests` להוריד artifacts (כמו bootloader ו-FPGA bitstream) לקבצים זמניים. `_flash_firmware` אז קורא ל-`jtag_controller.flash_image(...)` עם הקבצים האלה. שגיאות נתפסות ומתועדות כך שכשלי provisioning נראים בבירור גם ב-logs וגם ב-ELK.

**שאלה 7:** איך מומש הלוגינג לאורך ה-framework?

**תשובה:** מודול `logging` של Python משמש בהרחבה. ב-`conftest.py`, `logging.basicConfig` מגדיר stream ו-file logging (`test_execution.log`). `run_tests.py` ומודולים אחרים מקבלים module-level loggers דרך `logging.getLogger(__name__)`. בנוסף, `ELKReporter` משמש לדחיפת structured logs (עם הקשר כמו test name, board type ו-build version) ל-Elasticsearch.

**שאלה 8:** איך מומש איסוף metrics ב-framework?

**תשובה:** איסוף metrics מומש דרך `PrometheusReporter` ומוגדר תחת הסעיף `reporting.prometheus` של `config.yaml`. ה-orchestrator מתעד hardware-control metrics (למשל power-cycle duration) ודוחף metrics ל-Prometheus Pushgateway בזמן cleanup. בדיקות יכולות גם לדחוף metrics משלהן באמצעות אותו reporter.

**שאלה 9:** איך מומש מנגנון ה-cleanup וההבטחה שהלוח נשאר במצב בטוח?

**תשובה:** גם ה-orchestrator וגם pytest fixtures כוללים לוגיקת cleanup. ב-`TestOrchestrator.cleanup`, הקוד מבטיח שה-power controller משאיר את הלוח במצב `ON`. באופן דומה, ה-`power_controller` fixture ב-`conftest.py` בודק את מצב החשמל הסופי בבלוק `finally` ומדליק את הלוח במידת הצורך, מונע מבדיקות להשאיר חומרה במצב לא מוגדר.

**שאלה 10:** איך מומש TestOrchestrator class והאחריויות שלו?

**תשובה:** `TestOrchestrator` הוא המחלקה הראשית לתזמור בדיקות ZCU102 BSP. היא מתאמת את workflow הביצוע המלא כולל hardware provisioning, הרצת test suite ודיווח תוצאות. המחלקה מנהלת test session ID, deployment manifest, מצב hardware provisioning, ומאתחלת reporters (Prometheus, ELK) ו-hardware controllers (power, JTAG). היא מספקת methods כמו `provision_hardware`, `execute_test_suite`, `generate_final_report` ו-`cleanup`.
