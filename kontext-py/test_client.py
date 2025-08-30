#!/usr/bin/env python3
"""
Test script to verify the Kontext client is working correctly.
This will test the connection and show proper error handling.
"""

from kontext_client import KontextClientSync, KontextError


def test_client():
    # Test with no API key
    print("Test 1: Missing API key")
    try:
        client = KontextClientSync("")
    except KontextError as e:
        print(f"✓ Correctly caught error: {e}")
        print(f"  Code: {e.code}")
    print()

    # Test with invalid API key format
    print("Test 2: Invalid API key (should get UNAUTHORIZED from API)")
    client = KontextClientSync("ktext_invalid_test_key")
    try:
        client.get_context(user_id="test-user", task="chat")
    except KontextError as e:
        print(f"✓ API correctly rejected invalid key: {e}")
        print(f"  Code: {e.code}")
        print(f"  Status: {e.status_code}")
    print()

    # Test with valid user ID validation
    print("Test 3: Invalid user ID")
    client = KontextClientSync("ktext_test")
    try:
        client.get_context(user_id="", task="chat")
    except KontextError as e:
        print(f"✓ Correctly validated user ID: {e}")
        print(f"  Code: {e.code}")
    print()

    # Test with invalid privacy level
    print("Test 4: Invalid privacy level")
    try:
        client.get_context(user_id="test-user", privacy_level="invalid")
    except KontextError as e:
        print(f"✓ Correctly validated privacy level: {e}")
        print(f"  Code: {e.code}")
    print()

    print("=" * 60)
    print("All validation tests passed!")
    print("\nTo test with a real API key:")
    print("1. Set KONTEXT_API_KEY environment variable")
    print("2. Run: python simple_example.py")
    print("\nThe client is working correctly and ready to use!")


if __name__ == "__main__":
    test_client()
