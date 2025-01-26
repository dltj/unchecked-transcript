const { generate } = require("youtube-po-token-generator");
generate().then(
  (token) => {
    console.log(JSON.stringify(token));
  },
  (error) => {
    console.error(error);
  }
);
