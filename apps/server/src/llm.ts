import OpenAI from "openai";

import { config } from "./config.js";

export const client = new OpenAI({
  apiKey: config.openaiApiKey,
  baseURL: config.openaiBaseUrl,
});

export const MODEL = config.openaiModel;
