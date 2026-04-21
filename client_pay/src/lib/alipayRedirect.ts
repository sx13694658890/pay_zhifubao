/**
 * 将后端返回的支付宝表单 HTML 注入并提交（仅信任自家后端返回的内容）。
 */
export function submitAlipayFormHtml(formHtml: string): void {
  const host = document.createElement('div')
  host.setAttribute('data-alipay-form-host', '1')
  host.style.display = 'none'
  document.body.appendChild(host)
  host.innerHTML = formHtml

  const form = host.querySelector('form')
  if (!form) {
    document.body.removeChild(host)
    throw new Error('响应中未找到支付表单，请检查后端 form_html')
  }

  form.setAttribute('target', '_self')
  form.submit()
}

export function openAlipayPayUrl(payUrl: string): void {
  window.location.assign(payUrl)
}
