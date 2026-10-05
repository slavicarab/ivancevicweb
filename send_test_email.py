import json
import sys
import urllib.error
import urllib.request


def main():
    url = 'http://127.0.0.1:8001/contact'
    payload = {
        'name': 'Console Test',
        'company': 'Test Company',
        'email': 'console@example.com',
        'phone': '',
        'topic': 'Sonstiges / Noch nicht sicher',
        'budget': 'Noch nicht festgelegt',
        'message': 'This is a direct console test of the contact backend.',
        'privacy': True,
        'website': ''
    }

    if len(sys.argv) > 1:
        payload['message'] = ' '.join(sys.argv[1:])

    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    print(f'Sending test contact request to {url}')
    print('Payload:', payload)

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode('utf-8')
            print('Status:', response.status)
            print('Response:', body)
    except urllib.error.HTTPError as err:
        body = err.read().decode('utf-8', errors='replace')
        print('HTTP Error:', err.code)
        print('Response:', body)
    except urllib.error.URLError as err:
        print('Network error:', err.reason)
    except Exception as err:
        print('Unexpected error:', err)


if __name__ == '__main__':
    main()
