import { AccessToken } from 'livekit-server-sdk';
import { NextResponse } from 'next/server';


export async function GET(request: Request) {
  const room = new URL(request.url).searchParams.get('room') || 'sorborno-room';
  const participantName = `user-${Math.floor(Math.random() * 10000)}`;

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json({ error: 'Server misconfigured' }, { status: 500 });
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    ttl: '15m',
  });

  at.addGrant({ roomJoin: true, room: room });

  const token = await at.toJwt();

  return NextResponse.json({ token });
}

export const runtime = 'edge';
