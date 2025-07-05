from unittest import mock
from unittest.mock import patch, MagicMock

import pytest

from pytest_reporter_plus.send_email_report import send_email_from_env, load_email_env


@patch("smtplib.SMTP")
def test_send_email_success(mock_smtp):
    # Prepare mock environment
    config = {
        "sender_email": "sender@example.com",
        "recipient_email": "recipient@example.com",
        "report_path": "sample_report.html",
        "subject": "Test Subject",
        "smtp_server": "smtp.sendgrid.net",
        "smtp_port": "587",
        "email_password": "SG.fakekeyforunittesting"
    }

    with open(config["report_path"], "w") as f:
        f.write("<h1>Test Report</h1>")

    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    send_email_from_env(config)

    mock_smtp.assert_called_with("smtp.sendgrid.net", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("apikey", "SG.fakekeyforunittesting")
    mock_server.send_message.assert_called_once()


@patch("smtplib.SMTP")
def test_invalid_sendgrid_key_warning(mock_smtp, capsys):
    config = {
        "sender_email": "sender@example.com",
        "recipient_email": "recipient@example.com",
        "report_path": "sample_report.html",
        "subject": "Invalid Key Test",
        "smtp_server": "smtp.sendgrid.net",
        "smtp_port": "587",
        "email_password": "not_sendgrid_key"
    }

    with open(config["report_path"], "w") as f:
        f.write("test")

    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    send_email_from_env(config)

    captured = capsys.readouterr()
    assert "SendGrid API key looks invalid" in captured.out


def test_load_email_env_file_not_found():
    with pytest.raises(FileNotFoundError, match="emailenv file not found!"):
        load_email_env("non_existent_file.env")


def test_send_email_handles_exception(tmp_path):
    report_path = tmp_path / "report.html"
    report_path.write_text("<html><body>Fake report</body></html>")

    config = {
        "sender_email": "test@example.com",
        "recipient_email": "recipient@example.com",
        "report_path": str(report_path),
        "subject": "Test Report",
        "smtp_server": "smtp.sendgrid.net",
        "smtp_port": "587",
        "email_password": "SG.fakekey"
    }

    with mock.patch("smtplib.SMTP", side_effect=Exception("SMTP Error")):
        send_email_from_env(config)


def test_warns_on_invalid_sendgrid_key(tmp_path, capsys):
    report_path = tmp_path / "report.html"
    report_path.write_text("<html><body>Hi</body></html>")

    config = {
        "sender_email": "me@example.com",
        "recipient_email": "you@example.com",
        "report_path": str(report_path),
        "subject": "Fake Subject",
        "smtp_server": "smtp.sendgrid.net",
        "smtp_port": "587",
        "email_password": "INVALID_KEY"
    }

    with mock.patch("smtplib.SMTP", side_effect=Exception("SMTP failed")):
        send_email_from_env(config)

    captured = capsys.readouterr()
    assert "SendGrid API key looks invalid" in captured.out


def test_load_email_env_parses_file_correctly(tmp_path):
    env_file = tmp_path / "emailenv"
    env_file.write_text("sender_email=me@example.com\nrecipient_email=you@example.com\n")

    config = load_email_env(str(env_file))

    assert config["sender_email"] == "me@example.com"
    assert config["recipient_email"] == "you@example.com"
