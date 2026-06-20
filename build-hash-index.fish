#!/usr/bin/env fish
# build-hash-index.fish
# Builds the full pHash index for card scanning.
# Run with the backend server already running on port 8000.
# Usage: fish build-hash-index.fish

set BATCH_SIZE 500
set DELAY 3

echo "🔨 Building card scan hash index (batch size: $BATCH_SIZE)"
echo "   Make sure the backend is running: uvicorn app.main:app --port 8000"
echo ""

set total 0
while true
    set result (curl -s -X POST "http://localhost:8000/api/v1/scan/build-index?batch_size=$BATCH_SIZE")
    set indexed (echo $result | python3 -c "import json,sys; print(json.load(sys.stdin).get('indexed',0))" 2>/dev/null)

    if test "$indexed" = "0"
        echo ""
        echo "✅ Done! All cards with images have been indexed."
        break
    end

    set total (math $total + $indexed)
    echo -n "\r   Indexed: $total cards..."

    sleep $DELAY
end

echo "   Total hashes built: $total"
echo ""
echo "   Verify: curl -s http://localhost:8000/api/v1/scan/match -F image=@photo.jpg"
