import smtplib
from email.mime.text import MIMEText
from email.header import Header
import datetime

smtp_server = 'smtp.163.com'
smtp_port = 994

sender_email = 'cotalk2024@163.com'
sender_pwd = 'CRYGCQNSHIKEBYKX'


def send_email(receiver_email, content):
    try:
        # 创建SMTP连接
        smtp_connection = smtplib.SMTP_SSL(smtp_server, smtp_port)
        smtp_connection.helo(smtp_server)
        smtp_connection.ehlo(smtp_server)
        # 登录SMTP服务器
        smtp_connection.login(sender_email, sender_pwd)
        # 发送邮件
        smtp_connection.sendmail(sender_email, receiver_email, content)
        # 关闭连接
        smtp_connection.quit()
        print(f"email sent to {receiver_email}")
        return True
    except Exception as e:
        print(f"failed to send email to {receiver_email}: {e}")
        return False


def generate_email_content(receiver_email, code):
    content = MIMEText(
        f"""
<table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation">
  <tbody>
    <tr>
      <td><div style="margin:0px auto;max-width:600px;">
          <div style="line-height:0;font-size:0;">
            <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
              <tbody>
                <tr>
                  <td style="direction:ltr;font-size:0px;padding:20px 0;text-align:center;"><div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:middle;width:100%;">
                      <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:middle;" width="100%">
                        <tbody>
                          <tr>
                            <td align="center" style="font-size:0px;padding:10px 25px;padding-top:45px;padding-bottom:10px;word-break:break-word;"><div style="font-family:Ubuntu, Helvetica, Arial, sans-serif;font-size:24px;line-height:1;text-align:center;color:#45474e; font-weight: 200"> 
								<span style="font-size: 40px; line-height: 40px; font-weight: 400"> CoTalk Account</span><br />
                                <br />
								<br />
								Your verification code is
                                </div></td>
                          </tr>
                          <tr>
                            <td align="center" vertical-align="middle" style="font-size:0px;padding:10px 25px;padding-top:10px;padding-bottom:10px;word-break:break-word;"><table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:separate;line-height:100%;">
                                <tr>
                                  <td align="center" bgcolor="#CCCCCC" role="presentation" style="border:none;border-radius:5px;cursor:auto;mso-padding-alt:10px 25px;background:#CCCCCC;" valign="middle"><a style="display:inline-block;background:#CCCCCC;font-family:Ubuntu, Helvetica, Arial, sans-serif, Helvetica, Arial, sans-serif;font-size:25px;font-weight:300;line-height:120%;margin:0;text-decoration:none;text-transform:none;padding:20px 70px;color: black;mso-padding-alt:0px;border-radius:24px;" target="_blank"> {code} </a>
									</td>
                                </tr>
                              </table></td>
                          </tr>
							<tr>
                            <td align="center" style="font-size:0px;padding:10px 25px;padding-top:10px;padding-bottom:10px;word-break:break-word;"><div style="font-family:Ubuntu, Helvetica, Arial, sans-serif;font-size:10px;line-height:1;text-align:center;color:#45474e; font-weight: 200"> 
								Your verification code expires after 15 minutes.
                                </div></td>
                           </tr>
							<tr>
                            <td align="center" style="font-size:0px;padding:10px 25px;padding-top:20px;padding-bottom:10px;word-break:break-word;"><div style="font-family:Ubuntu, Helvetica, Arial, sans-serif;font-size:12px;line-height:1;text-align:center;color:#45474e; font-weight: 200"> 
								Someone is going to change your password at {datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}. 
								<br><br>
								If it is not your action, your password may be compromised.
                                </div></td>
                           </tr>
                        </tbody>
                      </table>
                    </div>
                    
                    <!--[if mso | IE]></td></tr></table><![endif]--></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!--[if mso | IE]></td></tr></table></v:textbox></v:rect><![endif]--></td>
    </tr>
  </tbody>
</table>
        """
        , 'html')
    content['To'] = receiver_email
    content['Subject'] = Header('CoTalk Account Verification Code', 'utf-8')
    return content


if __name__ == "__main__":
    receiver_email = 'fjs22@mails.tsinghua.edu.cn'
    code = '237922'
    content = generate_email_content(receiver_email, code)
    send_email(receiver_email, content.as_string())
