import { NextResponse } from "next/server";

const FASTAPI_BASE_URL = (process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await fetch(`${FASTAPI_BASE_URL}/api/coach`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "Coaching request failed." },
      { status: 500 }
    );
  }
}
