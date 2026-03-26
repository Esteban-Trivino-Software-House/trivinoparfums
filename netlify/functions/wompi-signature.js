const crypto = require('crypto');

exports.handler = async (event) => {
  // Solo aceptar POST
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: 'Invalid JSON' }) };
  }

  const { reference, amountInCents, currency = 'COP' } = body;

  if (!reference || !amountInCents) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Faltan parámetros: reference, amountInCents' }) };
  }

  const secret = process.env.WOMPI_INTEGRITY_SECRET;
  if (!secret) {
    return { statusCode: 500, body: JSON.stringify({ error: 'Integrity secret no configurado' }) };
  }

  // Fórmula oficial Wompi: SHA256(reference + amountInCents + currency + integritySecret)
  const str = `${reference}${amountInCents}${currency}${secret}`;
  const signature = crypto.createHash('sha256').update(str).digest('hex');

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ signature, reference, amountInCents, currency }),
  };
};
