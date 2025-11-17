# Tests Execution - שאלות ותשובות

**שאלה 1:** איך מריצים ידנית את חבילת הבדיקות מה-Test Host ואיך מוגדרות חבילות הבדיקה השונות?

**תשובה:** הרצה ידנית נעשית מתיקיית הפרויקט על Test Host:
```bash
python test_host/run_tests.py \
    --config test_host/config.yaml \
    --test-suite smoke
```
או באמצעות convenience scripts כמו `run_tests_with_bsp_manifest`. חבילות הבדיקה מוגדרות ב-`test_host/config.yaml` תחת `test_suites`:
- `smoke` - בדיקה מהירה של פונקציונליות ליבה (15 דקות)
- `regression` - בדיקה מקיפה של כל התכונות העיקריות (60 דקות)  
- `full` - בדיקה מורחבת כולל stress ו-longevity tests (240 דקות)
כל חבילה מכילה רשימת בדיקות לוגיות (boot_sequence, uart_basic, network_performance) וזמן timeout גלובלי.

**שאלה 2:** איך מוגדרות אפשרויות pytest command-line ומה התפקיד שלהן?

**תשובה:** ב-`test_host/tests/conftest.py`, `pytest_addoption` רושם אפשרויות כמו:
- `--config-file` (נתיב לקובץ YAML config)
- `--board-type` (למשל `zcu102`)
- `--build-version` (גרסת BSP תחת בדיקה)
- `--test-suite` (`smoke`, `regression`, `full`)
- `--skip-hardware` ו-`--power-cycle`
`run_tests.py` מעביר את האפשרויות האלה ל-pytest כשהוא מפעיל את הרצת הבדיקות.

**שאלה 3:** איך נשלטת הרצה תלוית חומרה מול mock execution?

**תשובה:** בדיקות תלויות חומרה מסומנות עם `@pytest.mark.hardware`. ב-`pytest_runtest_setup`, בדיקות כאלה מדולגות אוטומטית אם `--skip-hardware` מוגדר. בנוסף, fixtures כמו `power_controller` ו-`jtag_controller` יוצרים mock controllers כשהדגל `skip_hardware` מופעל בקונפיגורציה.

**שאלה 4:** איך pytest fixtures מנהלים משאבי חומרה?

**תשובה:** Fixtures ב-`conftest.py` מנהלים משאבי חומרה:
- `power_controller` - מאתחל בקר חשמל ומבטיח שהלוח נשאר דלוק אחרי בדיקות
- `jtag_controller` - מאתחל בקר JTAG לפעולות recovery
- `boot_validator` - מקים חיבור serial לבדיקת boot sequence
- `uart_tester` - מקים חיבור serial לבדיקות UART
כל fixture כולל לוגיקת cleanup ב-`finally` blocks.

**שאלה 5:** איך מוגדרים pytest markers ומה השימוש בהם?

**תשובה:** ב-`pytest_configure`, markers מוגדרים כמו:
- `boot` - בדיקות boot sequence validation
- `uart` - בדיקות תקשורת UART
- `ethernet` - בדיקות רשת Ethernet
- `gpio` - בדיקות פונקציונליות GPIO
- `hardware` - בדיקות הדורשות חומרה פיזית
- `slow` - בדיקות עם זמן ביצוע מורחב
Markers מאפשרים הרצה סלקטיבית של בדיקות ושליטה בהתנהגות.

**שאלה 6:** איך TestOrchestrator מבצע הרצת test suite?

**תשובה:** ב-`execute_test_suite` method, TestOrchestrator בונה פקודת pytest עם:
- נתיב לתיקיית tests
- פרמטרים כמו `--test-suite`, `--board-type`, `--build-version`
- אפשרויות pytest כמו `--verbose`, `--html=test_report.html`
- דגל `--skip-hardware` אם mock mode מופעל
הפקודה מורצת עם `subprocess.run` עם timeout של שעה אחת.

**שאלה 7:** איך מטופלים timeouts ו-error handling בהרצת בדיקות?

**תשובה:** הרצת בדיקות כוללת מספר רמות של timeout handling:
- Global timeout ברמת test suite (מוגדר ב-`config.yaml`)
- Subprocess timeout של 3600 שניות ב-`execute_test_suite`
- Individual test timeouts דרך pytest-timeout plugin
- Jenkins pipeline timeout של 3 שעות
שגיאות נתפסות ומתועדות ב-ELK עם הקשר מלא.

**שאלה 8:** איך מתבצע logging ו-metrics collection במהלך הרצת בדיקות?

**תשובה:** במהלך הרצת בדיקות:
- Python logging מתועד ל-`test_execution.log` ו-console
- ELKReporter דוחף structured logs ל-Elasticsearch עם metadata כמו test name, board type, build version
- PrometheusReporter אוסף metrics כמו test duration, success rate
- pytest מייצר HTML reports ו-JUnit XML לארכיון ב-Jenkins
כל הלוגים והמטריקות קשורים ל-test session ID ייחודי.

**שאלה 9:** איך מתבצעת הרצה עם BSP manifest?

**תשובה:** כשמשתמשים ב-BSP manifest:
- TestOrchestrator קורא ל-`parse_deployment_manifest` לפרסור ה-manifest
- המידע מה-manifest (build version, artifacts, test plan) מתווסף לקונפיגורציה
- אם מוגדר test plan ב-manifest, הוא דורס את ברירת המחדל
- Artifacts מורדים ו-firmware נטען לפני הרצת הבדיקות
- כל המידע מה-manifest נכלל בדיווח הסופי לtraceability מלא.

**שאלה 10:** איך מתבצע cleanup ו-post-execution actions?

**תשובה:** לאחר הרצת בדיקות:
- TestOrchestrator קורא ל-`cleanup()` method
- ELKReporter מבצע `flush_buffered_logs()` ו-`close()`
- PrometheusReporter דוחף metrics אחרונים עם session metadata
- Power controller מבטיח שהלוח נשאר במצב ON
- Jenkins אוסף test results, logs ו-screenshots מה-Test Host
- Notifications נשלחות ל-Slack ו-email עם תוצאות הבדיקה
- Test artifacts מארכבים לשמירה היסטורית.
