-- Executado pelo Wireshark da entrega; encerra após ler os quadros da cópia.
local count = 0
local tap = Listener.new("frame")
function tap.packet()
    count = count + 1
end
function tap.draw()
    if count > 0 then
        print("CARDEAL_WIRESHARK_GUI=" .. tostring(gui_enabled()) .. "; QUADROS=" .. tostring(count))
        os.exit(0)
    end
end
