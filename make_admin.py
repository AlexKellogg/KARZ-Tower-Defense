import argparse

from backend import AccountError
from local_backend import LocalBackend


def main():
    parser = argparse.ArgumentParser(description='Give an existing KARZ account admin privileges on this computer.')
    parser.add_argument('email', help='Email of an account that has already signed up')
    args = parser.parse_args()
    backend = LocalBackend()
    try:
        account = backend.promote_by_email(args.email)
        print(f'{account.username} ({account.email}) is now an admin. Log out and back in to see admin features.')
    except AccountError as e:
        print(e)
        raise SystemExit(1)
    finally:
        backend.close()


if __name__ == '__main__':
    main()
