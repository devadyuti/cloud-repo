const amplifyConfig = {
  Storage: {
    S3: {
      bucket: process.env.REACT_APP_S3_BUCKET || '',
      region: process.env.REACT_APP_AWS_REGION || 'eu-west-1',
    },
  },
  Auth: {
    Cognito: {
      identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID || '',
      allowGuestAccess: true,
    },
  },
};

/**
 * Validates the Amplify configuration object has all required fields.
 * @param {object} config - The Amplify configuration object
 * @throws {Error} If any required field is missing or empty
 */
function validateConfig(config) {
  if (!config?.Storage?.S3?.bucket) {
    throw new Error(
      'Amplify configuration error: Missing required field "Storage.S3.bucket". Set the REACT_APP_S3_BUCKET environment variable.'
    );
  }

  if (!config?.Storage?.S3?.region) {
    throw new Error(
      'Amplify configuration error: Missing required field "Storage.S3.region". Set the REACT_APP_AWS_REGION environment variable.'
    );
  }

  if (!config?.Auth?.Cognito?.identityPoolId) {
    throw new Error(
      'Amplify configuration error: Missing required field "Auth.Cognito.identityPoolId". Set the REACT_APP_IDENTITY_POOL_ID environment variable.'
    );
  }
}

export { amplifyConfig, validateConfig };
