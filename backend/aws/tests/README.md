# AWS Utilities Tests

This directory contains test cases for the AWS utilities.

## Setup

Before running the tests, ensure you have set the following environment variables:



You can set these in your  file in the backend directory.

## Running the Tests

To run all tests, from the  directory:



To run a specific test file:



## Test Structure

The tests are organized as follows:

- : Tests for S3 operations (listing files, retrieving content)

## Mock Testing

To avoid making actual AWS API calls during testing, many tests use the  module to mock the AWS SDK responses. This allows testing without requiring an actual AWS connection.

## Adding New Tests

When adding new tests:

1. Create a new test method in the appropriate test class
2. Use docstrings to explain what the test is checking
3. Follow the naming convention of 